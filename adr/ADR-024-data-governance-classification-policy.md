---
adr: 024
title: "Data Governance & Classification Policy"
status: "Accepted with notes"
date: "2026-05-30"
deciders:
  - "Faiz (Owner, solo developer Indonesia)"
  - "Guinevere (Executor / autonomous system steward)"
tags:
  - data-governance
  - classification
  - privacy
  - compliance
risk_level: "CRITICAL"
supersedes: "N/A"
related_documents:
  - Guinevere_MemorySchema_v2.0.md
  - Guinevere_PRD_v2.0.md
  - Guinevere_TechnicalArchitecture_v2.0.md
  - Guinevere_APIIntegration_v2.0.md
---

# ADR-024: Data Governance & Classification Policy

## Status

Accepted with notes

## Date

2026-05-30

## Deciders

Faiz (Owner, solo developer Indonesia); Guinevere (Executor / autonomous system steward)

## Tags

data-governance, classification, privacy, compliance

## Risk Level

CRITICAL

## Supersedes

N/A

## Related Documents

| Document | Relationship |
|---|---|
| [`../Guinevere_MemorySchema_v2.0.md`](../Guinevere_MemorySchema_v2.0.md) | Guinevere_MemorySchema_v2.0.md |
| [`../Guinevere_PRD_v2.0.md`](../Guinevere_PRD_v2.0.md) | Guinevere_PRD_v2.0.md |
| [`../Guinevere_TechnicalArchitecture_v2.0.md`](../Guinevere_TechnicalArchitecture_v2.0.md) | Guinevere_TechnicalArchitecture_v2.0.md |
| [`../Guinevere_APIIntegration_v2.0.md`](../Guinevere_APIIntegration_v2.0.md) | Guinevere_APIIntegration_v2.0.md |

## Context

Guinevere stores and processes personal, intimate, surveillance, financial, client, operational, and security-sensitive data. Current docs require a formal classification layer.

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

1. Classify data informally
2. Use only secret vs non-secret
3. Create explicit multi-class governance

## Decision Outcome

Chosen option: **Create explicit multi-class governance**.

Create a data governance and classification policy with classes for public, internal, personal, intimate, surveillance, financial, client-confidential, secret, and audit/evidence data. Every store, API, log, and memory path must map to a data class.

## Consequences

### Positive

- Enables retention, encryption, access control, and logging decisions
- Supports future DPIA/compliance docs
- Clarifies what sub-agents may see

### Negative

- Requires tagging and policy enforcement
- Can slow integration design

### Risks

- Misclassification can leak sensitive data
- Over-classification can reduce system usefulness

## Implementation Notes

- Implementation must update the relevant v2.0 source documents or future superseding specs if this ADR changes state.
- Accepted ADRs must not be edited in-place for material decision changes; create a superseding ADR instead.
- Proposed ADRs require Faiz approval before they become binding runtime policy.
- Any sub-agent research, implementation summary, audit, or verification used for this ADR must be written to markdown evidence, not returned only inline.

## Links

- [`../Guinevere_MemorySchema_v2.0.md`](../Guinevere_MemorySchema_v2.0.md)
- [`../Guinevere_PRD_v2.0.md`](../Guinevere_PRD_v2.0.md)
- [`../Guinevere_TechnicalArchitecture_v2.0.md`](../Guinevere_TechnicalArchitecture_v2.0.md)
- [`../Guinevere_APIIntegration_v2.0.md`](../Guinevere_APIIntegration_v2.0.md)
- [`../Guinevere_ADR_Index_v1.0.md`](../Guinevere_ADR_Index_v1.0.md)

## Review Record

- Reviewer: Guinevere Sub-Agent Reviewer
- Review Date: 2026-05-30
- Decision: Accepted with notes
- Notes: Accepted with notes: multi-class governance is comprehensive and consistent with memory schema and architecture docs. Note to add explicit PII mapping table per data class and integration with encryption key hierarchy defined in ADR-008.
