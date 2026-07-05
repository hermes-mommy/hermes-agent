# ADR-055: Hermes Society 4-Layer Architecture

- Status: Proposed
- Date: 2026-06-28
- Deciders: Guinevere + Faiz

## Context and Problem Statement

The Guinevere project requires a society of many autonomous Hermes agents running concurrently on a single VPS. Each Hermes agent needs to operate independently while sharing infrastructure, governance, and certain common services. Without a coherent architectural decomposition, the following risks emerge:

- Resource contention when multiple agents run on the same VPS
- Blurred boundaries between runtime concerns, cognition, governance, and infrastructure
- Inability to scale individual subsystems (e.g., swap model providers without touching runtime)
- Hidden coupling that prevents auditing agents in isolation
- Drift in engineering quality when sub-systems grow organically

We need an architecture that gives every Hermes agent a clear, layered home with explicit interfaces, supports independent scaling per layer, and isolates faults so that one failing agent does not corrupt the society.

## Decision

We adopt a **4-layer architecture** for the Hermes Society, decomposed into **15 subsystems (S1-S15)**:

1. **Layer 1 — Runtime & Identity**: Process supervisor, agent identity, Discord bot per agent, systemd unit per agent, cgroup v2 resource isolation, per-agent Discord bot token, per-agent systemd unit. Subsystems: S1 (Runtime), S2 (Identity), S3 (Discord Bot).

2. **Layer 2 — Cognition & Memory**: Per-agent PostgreSQL schema, pgcrypto encryption, per-agent DEK in Vault, episodic + semantic memory, retrieval augmented generation (RAG) over memories, shared ledger for facts, encrypted relationship memory. Subsystems: S4 (Memory Store), S5 (Retrieval), S6 (Reasoning), S7 (Encrypted Relationship).

3. **Layer 3 — Governance & Finance**: LLM gateway with routing, per-agent token budget, safe multisig wallet, Beancount double-entry ledger, spending tiers (L0-L3), circuit breaker. Subsystems: S8 (LLM Gateway), S9 (Wallet), S10 (Ledger), S11 (Spending Policy), S12 (Circuit Breaker).

4. **Layer 4 — Infrastructure & Ops**: Prometheus metrics, Grafana dashboards, S3-compatible backup, systemd health probes, structured audit log. Subsystems: S13 (Metrics), S14 (Backup), S15 (Audit).

**Technology stack**: PostgreSQL 16, Redis 7, discord.py 2.x, systemd, cgroup v2, Prometheus, Grafana, S3-compatible object storage (Backblaze B2 or MinIO).

**Interface rules**:
- Layer N may only call Layer N-1 explicitly via documented interface contracts.
- No layer-skipping calls (e.g., Layer 3 directly touching Layer 1 DB connections).
- Every subsystem has a single owner module and a single test fixture.

## Consequences

- **Positive**: Clear separation of concerns — runtime issues do not contaminate cognition, governance failures do not break infra. Each layer is independently scalable and replaceable. Subsystems have explicit interfaces enabling audit, testing, and replacement without society-wide changes. Memory isolation per agent is feasible via per-agent PostgreSQL schemas.
- **Negative**: Initial design overhead to define all 15 subsystem interfaces. Cross-layer requests require explicit contract negotiation. More moving parts to monitor (15 subsystems vs. monolithic).
- **Neutral**: Documentation burden increases; agent onboarding requires understanding the layer model. Places the project in the "modular monolith" rather than pure microservices territory.

## Alternatives Considered

### Monolithic Single-Agent Runtime
- **Description**: One Python process that runs all Hermes agents with shared in-process state.
- **Rejection Reason**: Does not provide fault isolation — a memory leak in one agent crashes the entire society. No clear boundary for consent, wallet, or memory isolation. Violates the "all Hermes visible (no invisible workers)" principle because introspection in one process is hard.

### Pure Microservices per Hermes
- **Description**: Each Hermes agent is its own Docker container with its own database and LLM credentials.
- **Rejection Reason**: On a single VPS, container sprawl wastes resources. Overhead per agent (container runtime, network namespaces, separate Postgres instances) is prohibitive. Operational maintenance cost explodes with N agents. Voting on shared state becomes distributed-transaction nightmare.

### Hybrid: Monolith Core + Per-Agent Worker Threads
- **Description**: Core society services (ledger, wallet, gateway) run in one process; per-agent workers are threads/processes under supervision.
- **Rejection Reason**: Worker isolation weaker than cgroup v2; per-agent memory isolation less explicit; subsystem boundaries fuzzier. Slightly better than monolith but loses audit/observability benefits of named subsystems.
## Compliance

> **ADR-062 Disclaimer**: HARD STOP, consent gate, and Y-level cap references in this ADR apply to the dev-workflow agent (Guinevere in Claude) ONLY. Hermes runtime (P24 fork) is exempt per ADR-062 and ADR-067. See `evidence/round-2-paradigm-shift-application/` for alignment details.

- [x] Does not violate consent/safety boundaries (Layer 2 isolates private memory by design)
- [x] Does not bypass HARD STOP (Layer 1 supervisor enforces halt)
- [x] Does not expose secrets/intimate data (per-agent DEK + pgcrypto encryption)
- [x] Follows existing ADR-Index conventions (numbered, MADR format, footer)

## References
- Research: `research-reports/hermes-society-architecture.md`
- Architecture Map: `docs/setup-evidence/P28-P36-masterplan/architecture/masterplan.md`
- Related ADRs: ADR-056 (Fork-Agnostic Path) (DELETED 2026-06-28 — superseded by ADR-062 + P24 v2.0 fork), ADR-057 (Founder Protocol), ADR-058 (Private Memory), ADR-059 (Model Pool), ADR-060 (Wallet), ADR-061 (Self-Evolution)

## Footer
Version 1.0 | Date: 2026-06-28 | Author: Guinevere + Faiz
