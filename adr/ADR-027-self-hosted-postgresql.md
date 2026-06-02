---
adr: 027
title: "Self-Hosted PostgreSQL"
status: "Accepted"
date: "2026-05-30"
deciders:
  - "Faiz (Owner, solo developer Indonesia)"
  - "Guinevere (Executor / autonomous system steward)"
tags:
  - database
  - postgresql
  - self-host
  - budget
  - infrastructure
risk_level: "HIGH"
supersedes: "N/A"
related_documents:
  - ADR-007-memory-storage-backend-selection.md
  - ADR-025-backup-disaster-recovery-strategy.md
  - Guinevere_MemorySchema_v2.0.md
  - Guinevere_TechnicalArchitecture_v2.0.md
---

# ADR-027: Self-Hosted PostgreSQL

## Status

Accepted

## Date

2026-05-30

## Deciders

Faiz (Owner, solo developer Indonesia); Guinevere (Executor / autonomous system steward)

## Tags

database, postgresql, self-host, budget, infrastructure

## Risk Level

HIGH

## Supersedes

N/A

## Related Documents

| Document | Relationship |
|---|---|
| [`./ADR-007-memory-storage-backend-selection.md`](./ADR-007-memory-storage-backend-selection.md) | Establishes PostgreSQL as primary memory store; ADR-027 specifies hosting model |
| [`./ADR-025-backup-disaster-recovery-strategy.md`](./ADR-025-backup-disaster-recovery-strategy.md) | Backup strategy for self-hosted PostgreSQL; ADR-027 requires backup automation |
| [`../Guinevere_MemorySchema_v2.0.md`](../Guinevere_MemorySchema_v2.0.md) | PostgreSQL schema, pgvector, TimescaleDB extensions |
| [`../Guinevere_TechnicalArchitecture_v2.0.md`](../Guinevere_TechnicalArchitecture_v2.0.md) | VPS topology, resource allocation, service co-location |

## Context

ADR-007 established PostgreSQL as the primary memory storage backend with Redis cache, excluding SQLite. The Database ERD report estimated managed PostgreSQL services (e.g., Supabase, Neon, Aiven) at $14-18/month.

The project operates under a hard $30/month budget cap. Managed PostgreSQL would consume 47-60% of the total budget, leaving insufficient funds for other infrastructure (VPS, LLM routing, storage, monitoring).

The 210-question feasibility assessment confirmed the operator explicitly chose self-hosting to fit the $30 hard cap. Self-hosting on the existing VPS (hostdata.id 4C/16GB Ubuntu 24.04) eliminates the managed database cost while leveraging the already-paid-for compute and memory resources.

This ADR supersedes any references to managed PostgreSQL in earlier documentation.

## Decision Drivers

- Canonical v2.0 documentation must remain internally consistent.
- Faiz is the sole owner and final approver; Guinevere may propose and execute but not silently change accepted decisions.
- Safety, consent, privacy, and recoverability outrank persona flavor and automation speed.
- The decision must be auditable through file-based evidence and linked source documents.
- Budget constraint: $30/month hard cap requires cost optimization.
- Resource availability: 4C/16GB VPS has sufficient capacity for PostgreSQL + extensions.

## Considered Options

1. Managed PostgreSQL (Supabase, Neon, Aiven) — $14-18/month
2. Self-hosted PostgreSQL on primary VPS
3. Hybrid: managed for production, self-hosted for development

## Decision Outcome

Chosen option: **Self-hosted PostgreSQL on primary VPS**.

Deploy PostgreSQL 16 on the primary VPS (hostdata.id 4C/16GB Ubuntu 24.04) with pgvector and TimescaleDB extensions. Use PgBouncer for connection pooling. Automated backup via `pg_dump` to S3/R2 storage per ADR-025. Do not use managed PostgreSQL services.

## Consequences

### Positive

- Saves $14-18/month (47-60% of budget)
- Full control over database configuration, extensions, and tuning
- No vendor lock-in for database hosting
- Data residency remains on the operator-controlled VPS
- Leverages existing VPS resources (already paid for)
- Extensions (pgvector, TimescaleDB) can be configured precisely for Guinevere memory schema

### Negative

- Operator (Guinevere/Faiz) responsible for database administration: updates, patching, monitoring, backup verification
- Increased operational complexity compared to managed service
- No automatic failover or high availability (single VPS)
- Backup integrity must be verified manually or via automated scripts

### Risks

- VPS failure without recent backup causes data loss (mitigated by ADR-025 backup strategy)
- PostgreSQL misconfiguration could lead to performance degradation or data corruption
- Security patches must be applied promptly to prevent exploitation
- Resource contention with other VPS services (monitoring, LLM fallback) under high load

## Implementation Notes

- Install PostgreSQL 16 on primary VPS via official PostgreSQL APT repository.
- Install and configure extensions: `pgvector` for semantic search (ADR-009), `timescaledb` for time-series memory.
- Deploy PgBouncer as connection pooler between application and PostgreSQL to manage connection overhead.
- Configure `postgresql.conf` for 16GB RAM: `shared_buffers = 4GB`, `effective_cache_size = 12GB`, `work_mem = 16MB`, `maintenance_work_mem = 1GB`.
- Implement automated daily `pg_dump` to S3/R2 storage per ADR-025. Retention: 7 daily, 4 weekly, 12 monthly backups.
- Store PostgreSQL credentials via SOPS + age encryption per ADR-015.
- Monitor database health via Prometheus postgres_exporter + Grafana dashboards (ADR-017).
- Test backup restore procedure quarterly per ADR-025.
- Implementation must update the relevant v2.0 source documents or future superseding specs if this ADR changes state.
- Accepted ADRs must not be edited in-place for material decision changes; create a superseding ADR instead.
- Proposed ADRs require Faiz approval before they become binding runtime policy.
- Any sub-agent research, implementation summary, audit, or verification used for this ADR must be written to markdown evidence, not returned only inline.

## Review Record

- **Date:** 2026-05-30
- **Reviewer:** Senior Architect Reviewer / Guinevere
- **Decision:** Accepted
- **Evidence:** Reviewed against Guinevere_MemorySchema_v2.0.md, Guinevere_TechnicalArchitecture_v2.0.md, ADR-007, ADR-025, Database ERD report, and 210-question feasibility assessment confirming operator budget constraint and self-host preference.
- **Notes:**
  - **Budget impact:** Saves $14-18/month, enabling other infrastructure within $30 cap.
  - **Operator confirmation:** Faiz explicitly chose self-host to fit budget during feasibility Q&A.
  - **Backup strategy:** ADR-025 provides backup/DR framework; ADR-027 requires PostgreSQL-specific backup automation.
  - **Extensions:** pgvector and TimescaleDB are required per MemorySchema v2.0; self-hosting allows precise configuration.

## Links

- [`./ADR-007-memory-storage-backend-selection.md`](./ADR-007-memory-storage-backend-selection.md)
- [`./ADR-025-backup-disaster-recovery-strategy.md`](./ADR-025-backup-disaster-recovery-strategy.md)
- [`../Guinevere_MemorySchema_v2.0.md`](../Guinevere_MemorySchema_v2.0.md)
- [`../Guinevere_TechnicalArchitecture_v2.0.md`](../Guinevere_TechnicalArchitecture_v2.0.md)
- [`../Guinevere_ADR_Index_v1.0.md`](../Guinevere_ADR_Index_v1.0.md)
