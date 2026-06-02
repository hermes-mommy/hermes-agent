---
adr: 010
title: "Surveillance Data Retention Policy"
status: "Accepted with notes"
date: "2026-05-30"
deciders:
  - "Faiz (Owner, solo developer Indonesia)"
  - "Guinevere (Executor / autonomous system steward)"
tags:
  - surveillance
  - privacy
  - retention
  - single-user
risk_level: "HIGH"
supersedes: "N/A"
related_documents:
  - Guinevere_PRD_v2.0.md
  - Guinevere_TechnicalArchitecture_v2.0.md
  - Guinevere_APIIntegration_v2.0.md
  - Guinevere_MemorySchema_v2.0.md
---

# ADR-010: Surveillance Data Retention Policy

## Status

Proposed

## Date

2026-05-30

## Deciders

Faiz (Owner, solo developer Indonesia); Guinevere (Executor / autonomous system steward)

## Tags

surveillance, privacy, retention, single-user

## Risk Level

HIGH

## Supersedes

N/A

## Related Documents

| Document | Relationship |
|---|---|
| [`../Guinevere_PRD_v2.0.md`](../Guinevere_PRD_v2.0.md) | Guinevere_PRD_v2.0.md |
| [`../Guinevere_TechnicalArchitecture_v2.0.md`](../Guinevere_TechnicalArchitecture_v2.0.md) | Guinevere_TechnicalArchitecture_v2.0.md |
| [`../Guinevere_APIIntegration_v2.0.md`](../Guinevere_APIIntegration_v2.0.md) | Guinevere_APIIntegration_v2.0.md |
| [`../Guinevere_MemorySchema_v2.0.md`](../Guinevere_MemorySchema_v2.0.md) | Guinevere_MemorySchema_v2.0.md |

## Context

Guinevere is a single-user private system for Faiz with full consent for surveillance integrations. Even with consent, raw surveillance data is sensitive and needs retention limits, summarization policy, and deletion/export paths.

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

## Considered Options

1. Retain everything indefinitely
2. Delete raw data immediately
3. Retain by data class with minimization and export/delete controls

## Decision Outcome

Chosen option: **Retain by data class with minimization and export/delete controls**.

Create a retention policy that differentiates raw telemetry, summaries, derived facts, emotional annotations, financial data, and audit logs. Default to minimizing raw retention, preserving explicit summaries and evidence where needed, and supporting Faiz-controlled deletion/export.

## Consequences

### Positive

- Respects consent without hoarding sensitive raw data
- Supports future DPIA and compliance mapping
- Clarifies memory consolidation behavior

### Negative

- Requires data classification and lifecycle jobs
- Some debugging history may be unavailable after expiry

### Risks

- Retention bugs can either over-delete evidence or over-retain private data
- Consent scope must be revisited if system becomes multi-user

## Implementation Notes

- Implementation must update the relevant v2.0 source documents or future superseding specs if this ADR changes state.
- Accepted ADRs must not be edited in-place for material decision changes; create a superseding ADR instead.
- Proposed ADRs require Faiz approval before they become binding runtime policy.
- Any sub-agent research, implementation summary, audit, or verification used for this ADR must be written to markdown evidence, not returned only inline.

## Links

- [`../Guinevere_PRD_v2.0.md`](../Guinevere_PRD_v2.0.md)
- [`../Guinevere_TechnicalArchitecture_v2.0.md`](../Guinevere_TechnicalArchitecture_v2.0.md)
- [`../Guinevere_APIIntegration_v2.0.md`](../Guinevere_APIIntegration_v2.0.md)
- [`../Guinevere_MemorySchema_v2.0.md`](../Guinevere_MemorySchema_v2.0.md)
- [`../Guinevere_ADR_Index_v1.0.md`](../Guinevere_ADR_Index_v1.0.md)

## Review Record

- Reviewer: Guinevere Sub-Agent Reviewer
- Review Date: 2026-05-30
- Decision: Accepted with notes
- Notes: Accepted with notes: retention-by-class and consent are documented appropriately for single-user context. Note to add explicit data-minimization checklist and GDPR-style DPIA mapping reference if scope ever expands beyond single-user.
