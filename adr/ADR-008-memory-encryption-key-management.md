---
adr: 008
title: "Memory Encryption & Key Management"
status: "Accepted with notes"
date: "2026-05-30"
deciders:
  - "Faiz (Owner, solo developer Indonesia)"
  - "Guinevere (Executor / autonomous system steward)"
tags:
  - memory
  - encryption
  - keys
  - privacy
risk_level: "CRITICAL"
supersedes: "N/A"
related_documents:
  - Guinevere_MemorySchema_v2.0.md
  - Guinevere_TechnicalArchitecture_v2.0.md
  - Guinevere_APIIntegration_v2.0.md
---

# ADR-008: Memory Encryption & Key Management

## Status

Accepted with notes

## Date

2026-05-30

## Deciders

Faiz (Owner, solo developer Indonesia); Guinevere (Executor / autonomous system steward)

## Tags

memory, encryption, keys, privacy

## Risk Level

CRITICAL

## Supersedes

N/A

## Related Documents

| Document | Relationship |
|---|---|
| [`../Guinevere_MemorySchema_v2.0.md`](../Guinevere_MemorySchema_v2.0.md) | Guinevere_MemorySchema_v2.0.md |
| [`../Guinevere_TechnicalArchitecture_v2.0.md`](../Guinevere_TechnicalArchitecture_v2.0.md) | Guinevere_TechnicalArchitecture_v2.0.md |
| [`../Guinevere_APIIntegration_v2.0.md`](../Guinevere_APIIntegration_v2.0.md) | Guinevere_APIIntegration_v2.0.md |

## Context

Guinevere memory contains intimate persona data, surveillance-derived facts, financial signals, client context, and operational secrets-adjacent metadata. The seed docs mention encryption but do not fully define key hierarchy, rotation, or access boundaries.

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

1. Rely only on disk/database encryption
2. Encrypt selected fields without formal key policy
3. Create explicit key hierarchy and rotation policy

## Decision Outcome

Chosen option: **Create explicit key hierarchy and rotation policy**.

Define memory encryption and key management as a dedicated architecture concern. Sensitive fields require encryption-at-rest, auditable key ownership, rotation procedure, emergency revoke path, and separation between secrets, profile memory, surveillance events, and operational logs.

## Consequences

### Positive

- Reduces blast radius for intimate data
- Creates prerequisites for compliance and backup safety
- Clarifies how SOPS/age and application encryption interact

### Negative

- Adds implementation and recovery complexity
- Key loss can make memory unrecoverable

### Risks

- Improper logging can bypass encryption
- Rotation mistakes can corrupt historical memory

## Implementation Notes

- Implementation must update the relevant v2.0 source documents or future superseding specs if this ADR changes state.
- Accepted ADRs must not be edited in-place for material decision changes; create a superseding ADR instead.
- Proposed ADRs require Faiz approval before they become binding runtime policy.
- Any sub-agent research, implementation summary, audit, or verification used for this ADR must be written to markdown evidence, not returned only inline.

## Links

- [`../Guinevere_MemorySchema_v2.0.md`](../Guinevere_MemorySchema_v2.0.md)
- [`../Guinevere_TechnicalArchitecture_v2.0.md`](../Guinevere_TechnicalArchitecture_v2.0.md)
- [`../Guinevere_APIIntegration_v2.0.md`](../Guinevere_APIIntegration_v2.0.md)
- [`../Guinevere_ADR_Index_v1.0.md`](../Guinevere_ADR_Index_v1.0.md)

## Review Record

- Reviewer: Guinevere Sub-Agent Reviewer
- Review Date: 2026-05-30
- Decision: Accepted with notes
- Notes: Accepted with notes: key hierarchy and rotation are well defined. Note to add explicit master-key recovery/break-glass procedure and key-escrow policy in a follow-up security runbook.
