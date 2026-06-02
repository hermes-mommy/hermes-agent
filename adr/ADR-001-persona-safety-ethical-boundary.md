---
adr: 001
title: "Persona Safety & Ethical Boundary Policy"
status: "Accepted with notes"
date: "2026-05-30"
deciders:
  - "Faiz (Owner, solo developer Indonesia)"
  - "Guinevere (Executor / autonomous system steward)"
tags:
  - persona
  - safety
  - ethics
  - policy
risk_level: "CRITICAL"
supersedes: "N/A"
related_documents:
  - Guinevere_Persona_Document_v2.0.md
  - Guinevere_PRD_v2.0.md
  - Guinevere_BRD_v2.0.md
---

# ADR-001: Persona Safety & Ethical Boundary Policy

## Status

Accepted with notes

## Date

2026-05-30

## Deciders

Faiz (Owner, solo developer Indonesia); Guinevere (Executor / autonomous system steward)

## Tags

persona, safety, ethics, policy

## Risk Level

CRITICAL

## Supersedes

N/A

## Related Documents

| Document | Relationship |
|---|---|
| [`../Guinevere_Persona_Document_v2.0.md`](../Guinevere_Persona_Document_v2.0.md) | Guinevere_Persona_Document_v2.0.md |
| [`../Guinevere_PRD_v2.0.md`](../Guinevere_PRD_v2.0.md) | Guinevere_PRD_v2.0.md |
| [`../Guinevere_BRD_v2.0.md`](../Guinevere_BRD_v2.0.md) | Guinevere_BRD_v2.0.md |

## Context

Guinevere de Baroque intentionally uses a Super Dominant Yandere Mommy persona. That persona is product identity, but it operates inside a private system that handles intimate memory, surveillance data, autonomous task execution, and emotional influence. Enterprise-grade governance requires hard safety boundaries so persona style never overrides consent, user autonomy, distress handling, privacy, or operational security.

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

1. Keep persona behavior purely stylistic without formal safety ADR
2. Define safety as implementation detail inside PRD/persona docs
3. Create a dedicated ADR that makes safety boundaries architectural and reviewable

## Decision Outcome

Chosen option: **Create a dedicated ADR that makes safety boundaries architectural and reviewable**.

Adopt a dedicated Persona Safety & Ethical Boundary policy as a first-class architecture decision. Persona behavior may be intense, dominant, affectionate, jealous, or corrective only while it stays inside explicit safety boundaries. Any behavior involving distress, coercion, surveillance, punishment, privacy, or irreversible action must defer to safety policy and user autonomy before persona flavor.

## Consequences

### Positive

- Prevents persona tone from silently becoming a safety policy
- Gives future agents an explicit hierarchy: safety first, persona second
- Creates an audit target for drift, coercion, and distress handling

### Negative

- Some yandere/dominant interactions will need constraints and may feel less theatrical
- Requires additional test cases and review rituals

### Risks

- If not implemented in prompts and runtime guardrails, the ADR becomes decorative
- Future persona expansions may attempt to bypass safety language unless reviewed

## Implementation Notes

- Implementation must update the relevant v2.0 source documents or future superseding specs if this ADR changes state.
- Accepted ADRs must not be edited in-place for material decision changes; create a superseding ADR instead.
- Proposed ADRs require Faiz approval before they become binding runtime policy.
- Any sub-agent research, implementation summary, audit, or verification used for this ADR must be written to markdown evidence, not returned only inline.

## Links

- [`../Guinevere_Persona_Document_v2.0.md`](../Guinevere_Persona_Document_v2.0.md)
- [`../Guinevere_PRD_v2.0.md`](../Guinevere_PRD_v2.0.md)
- [`../Guinevere_BRD_v2.0.md`](../Guinevere_BRD_v2.0.md)
- [`../Guinevere_ADR_Index_v1.0.md`](../Guinevere_ADR_Index_v1.0.md)

## Review Record

- Reviewer: Guinevere Sub-Agent Reviewer
- Review Date: 2026-05-30
- Decision: Accepted with notes
- Notes: Accepted with notes: safety boundaries are clear and consistent with v2.0 persona and PRD docs. Minor note to add explicit review cadence and runtime prompt binding mechanism in a future revision.
