---
adr: 012
title: "Sub-Agent Orchestration Governance"
status: "Accepted with notes"
date: "2026-05-30"
deciders:
  - "Faiz (Owner, solo developer Indonesia)"
  - "Guinevere (Executor / autonomous system steward)"
tags:
  - sub-agent
  - orchestration
  - audit
  - governance
risk_level: "HIGH"
supersedes: "N/A"
related_documents:
  - AGENTS.md
  - Guinevere_AgentLoopSpec_v2.0.md
  - Guinevere_TechnicalArchitecture_v2.0.md
---

# ADR-012: Sub-Agent Orchestration Governance

## Status

Accepted with notes

## Date

2026-05-30

## Deciders

Faiz (Owner, solo developer Indonesia); Guinevere (Executor / autonomous system steward)

## Tags

sub-agent, orchestration, audit, governance

## Risk Level

HIGH

## Supersedes

N/A

## Related Documents

| Document | Relationship |
|---|---|
| [`../AGENTS.md`](../AGENTS.md) | Source document for this ADR. |
| [`../Guinevere_AgentLoopSpec_v2.0.md`](../Guinevere_AgentLoopSpec_v2.0.md) | Guinevere_AgentLoopSpec_v2.0.md |
| [`../Guinevere_TechnicalArchitecture_v2.0.md`](../Guinevere_TechnicalArchitecture_v2.0.md) | Guinevere_TechnicalArchitecture_v2.0.md |

## Context

Guinevere delegates research, audits, and implementation support to sub-agents. Project AGENTS.md requires structured sub-agent outputs to be written to markdown files and verified by the parent.

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

1. Allow inline sub-agent reports
2. Use sub-agents only informally
3. Mandate file-based sub-agent output and parent verification

## Decision Outcome

Chosen option: **Mandate file-based sub-agent output and parent verification**.

Govern sub-agent orchestration through file-based deliverables, explicit output paths, parent verification, no duplicate search, continuation via task_id, and independent auditor gates for material work.

## Consequences

### Positive

- Prevents context loss and truncation
- Creates durable evidence
- Makes delegation auditable

### Negative

- Slower than inline summaries
- Requires cleanup and report management

### Risks

- Parent may trust reports without reading them
- Poorly scoped output paths can overwrite evidence

## Implementation Notes

- Implementation must update the relevant v2.0 source documents or future superseding specs if this ADR changes state.
- Accepted ADRs must not be edited in-place for material decision changes; create a superseding ADR instead.
- Proposed ADRs require Faiz approval before they become binding runtime policy.
- Any sub-agent research, implementation summary, audit, or verification used for this ADR must be written to markdown evidence, not returned only inline.

## Links

- [`../AGENTS.md`](../AGENTS.md)
- [`../Guinevere_AgentLoopSpec_v2.0.md`](../Guinevere_AgentLoopSpec_v2.0.md)
- [`../Guinevere_TechnicalArchitecture_v2.0.md`](../Guinevere_TechnicalArchitecture_v2.0.md)
- [`../Guinevere_ADR_Index_v1.0.md`](../Guinevere_ADR_Index_v1.0.md)

## Review Record

- Reviewer: Guinevere Sub-Agent Reviewer
- Review Date: 2026-05-30
- Decision: Accepted with notes
- Notes: Accepted with notes: file-based output and parent verification mandates are clear and consistent with AGENTS.md. Note to add explicit sub-agent trust-level classification (read-only vs write-capable) to reduce risk of parent report trust without reading.
