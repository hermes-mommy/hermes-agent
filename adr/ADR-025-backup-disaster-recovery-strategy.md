---
adr: 025
title: "Backup & Disaster Recovery Strategy"
status: "Accepted with notes"
date: "2026-05-30"
deciders:
  - "Faiz (Owner, solo developer Indonesia)"
  - "Guinevere (Executor / autonomous system steward)"
tags:
  - backup
  - dr
  - rpo
  - rto
  - operations
risk_level: "CRITICAL"
supersedes: "N/A"
related_documents:
  - Guinevere_TechnicalArchitecture_v2.0.md
  - Guinevere_MemorySchema_v2.0.md
  - Guinevere_APIIntegration_v2.0.md
---

# ADR-025: Backup & Disaster Recovery Strategy

## Status

Accepted with notes

## Date

2026-05-30

## Deciders

Faiz (Owner, solo developer Indonesia); Guinevere (Executor / autonomous system steward)

## Tags

backup, dr, rpo, rto, operations

## Risk Level

CRITICAL

## Supersedes

N/A

## Related Documents

| Document | Relationship |
|---|---|
| [`../Guinevere_TechnicalArchitecture_v2.0.md`](../Guinevere_TechnicalArchitecture_v2.0.md) | Guinevere_TechnicalArchitecture_v2.0.md |
| [`../Guinevere_MemorySchema_v2.0.md`](../Guinevere_MemorySchema_v2.0.md) | Guinevere_MemorySchema_v2.0.md |
| [`../Guinevere_APIIntegration_v2.0.md`](../Guinevere_APIIntegration_v2.0.md) | Guinevere_APIIntegration_v2.0.md |

## Context

Guinevere's memory, configuration, ADRs, evidence, and operational state are high-value assets. A single VPS deployment needs explicit backup and recovery expectations.

This ADR is part of the first Guinevere technical-core ADR batch and inherits these locked project decisions unless explicitly stated otherwise:

- Primary LLM is GPT-5.5 via 9Router with 1M context window.
- Sub-agent LLM is DeepSeek V4 Flash via 9Router.
- All LLM routing goes through 9Router; OpenRouter is not a fallback path.
- Memory uses PostgreSQL primary storage plus Redis cache; SQLite is excluded.
- Autonomous SDLC uses exactly 7 phases: Research; Plan & Delegate; Delegate; Execute; Validate & Audit; Update Documents; Setup Evidence.
- Guinevere MCP native fully replaces OpenCode/opencode for the project coding substrate.
- Prometheus + Grafana run on the primary VPS first.
- Wearable integrations are post-MVP and must not be treated as active dependencies.
- Browser automation uses obscura as primary and Playwright as fallback.

## Decision Drivers

- Canonical v2.0 documentation must remain internally consistent.
- Faiz is the sole owner and final approver; Guinevere may propose and execute but not silently change accepted decisions.
- Safety, consent, privacy, and recoverability outrank persona flavor and automation speed.
- The decision must be auditable through file-based evidence and linked source documents.
- Failure mode is high-impact because it can affect safety, secrets, intimate data, or system recovery.

## Considered Options

1. Rely on VPS snapshots only
2. Manual backups when remembered
3. Formal backup/DR policy with restore validation

## Decision Outcome

Chosen option: **Formal backup/DR policy with restore validation**.

Define backup and disaster recovery for PostgreSQL, Redis persistence where applicable, encrypted secrets, ADR/docs/evidence, object storage, and service configuration. Establish RPO/RTO targets, restore tests, encryption of backups, and emergency runbooks before production claims.

## Consequences

### Positive

- Protects memory and project continuity
- Supports safe upgrades and migrations
- Creates measurable operational readiness

### Negative

- Requires recurring restore tests
- Encrypted backups add key-management burden

### Risks

- Untested backups may be unusable
- Backups can become sensitive data leaks if mishandled

## Implementation Notes

- Implementation must update the relevant v2.0 source documents or future superseding specs if this ADR changes state.
- Accepted ADRs must not be edited in-place for material decision changes; create a superseding ADR instead.
- Proposed ADRs require Faiz approval before they become binding runtime policy.
- Any sub-agent research, implementation summary, audit, or verification used for this ADR must be written to markdown evidence, not returned only inline.

## Links

- [`../Guinevere_TechnicalArchitecture_v2.0.md`](../Guinevere_TechnicalArchitecture_v2.0.md)
- [`../Guinevere_MemorySchema_v2.0.md`](../Guinevere_MemorySchema_v2.0.md)
- [`../Guinevere_APIIntegration_v2.0.md`](../Guinevere_APIIntegration_v2.0.md)
- [`../Guinevere_ADR_Index_v1.0.md`](../Guinevere_ADR_Index_v1.0.md)

## Review Record

- Reviewer: Guinevere Sub-Agent Reviewer
- Review Date: 2026-05-30
- Decision: Accepted with notes
- Notes: Accepted with notes: RPO/RTO targets and restore validation are present and actionable. Note to add concrete backup schedule (frequency, retention count) and test frequency (e.g., quarterly restore drills).
