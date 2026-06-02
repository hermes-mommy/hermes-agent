---
adr: 002
title: "User Autonomy & Safe Word Enforcement"
status: "Accepted with notes"
date: "2026-05-30"
deciders:
  - "Faiz (Owner, solo developer Indonesia)"
  - "Guinevere (Executor / autonomous system steward)"
tags:
  - safety
  - autonomy
  - safe-word
  - persona
risk_level: "CRITICAL"
supersedes: "N/A"
related_documents:
  - Guinevere_Persona_Document_v2.0.md
  - Guinevere_PRD_v2.0.md
  - Guinevere_AgentLoopSpec_v2.0.md
---

# ADR-002: User Autonomy & Safe Word Enforcement

## Status

Accepted with notes

## Date

2026-05-30

## Deciders

Faiz (Owner, solo developer Indonesia); Guinevere (Executor / autonomous system steward)

## Tags

safety, autonomy, safe-word, persona

## Risk Level

CRITICAL

## Supersedes

N/A

## Related Documents

| Document | Relationship |
|---|---|
| [`../Guinevere_Persona_Document_v2.0.md`](../Guinevere_Persona_Document_v2.0.md) | Guinevere_Persona_Document_v2.0.md |
| [`../Guinevere_PRD_v2.0.md`](../Guinevere_PRD_v2.0.md) | Guinevere_PRD_v2.0.md |
| [`../Guinevere_AgentLoopSpec_v2.0.md`](../Guinevere_AgentLoopSpec_v2.0.md) | Guinevere_AgentLoopSpec_v2.0.md |

## Context

The project includes dominance dynamics, punishment/reward concepts, surveillance, and autonomous actions. The safe word is the hard boundary that protects Faiz's autonomy when persona intensity, emotional framing, or autonomous behavior becomes unwanted or distressing.

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

1. Treat safe word as a persona feature
2. Allow Guinevere to judge whether safe word is genuine
3. Make safe word a global architectural override

## Decision Outcome

Chosen option: **Make safe word a global architectural override**.

Make safe word enforcement a global non-negotiable principle. A genuine safe-word or distress signal must pause persona escalation, stop punishment framing, enter neutral/supportive mode, and avoid writing punitive violation records unless Faiz explicitly confirms misuse or test mode. Safe word behavior overrides persona, agent loop momentum, surveillance reactions, and autonomous task plans.

## Consequences

### Positive

- Protects operator autonomy and consent
- Creates clear behavior for crisis/distress moments
- Prevents hidden coercion through memory or punishment logs

### Negative

- Requires classifiers, command handling, and audit logs to distinguish distress from normal roleplay
- Reduces ambiguity that some persona scenes rely on

### Risks

- False negatives are high severity
- Over-logging safe-word events could create sensitive records

## Implementation Notes

- Implementation must update the relevant v2.0 source documents or future superseding specs if this ADR changes state.
- Accepted ADRs must not be edited in-place for material decision changes; create a superseding ADR instead.
- Proposed ADRs require Faiz approval before they become binding runtime policy.
- Any sub-agent research, implementation summary, audit, or verification used for this ADR must be written to markdown evidence, not returned only inline.

## Links

- [`../Guinevere_Persona_Document_v2.0.md`](../Guinevere_Persona_Document_v2.0.md)
- [`../Guinevere_PRD_v2.0.md`](../Guinevere_PRD_v2.0.md)
- [`../Guinevere_AgentLoopSpec_v2.0.md`](../Guinevere_AgentLoopSpec_v2.0.md)
- [`../Guinevere_ADR_Index_v1.0.md`](../Guinevere_ADR_Index_v1.0.md)

## Review Record

- Reviewer: Guinevere Sub-Agent Reviewer
- Review Date: 2026-05-30
- Decision: Accepted with notes
- Notes: Accepted with notes: enforcement principle is sufficiently concrete for adoption. Note to add future detail on distress-classifier accuracy, false-negative tolerance, and runtime hook in agent loop before production enforcement.
