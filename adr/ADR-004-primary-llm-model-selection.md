---
adr: 004
title: "Primary LLM Model Selection"
status: "Accepted"
date: "2026-05-30"
deciders:
  - "Faiz (Owner, solo developer Indonesia)"
  - "Guinevere (Executor / autonomous system steward)"
tags:
  - llm
  - model
  - 9router
  - canonical
risk_level: "HIGH"
supersedes: "N/A"
related_documents:
  - Guinevere_TechnicalArchitecture_v2.0.md
  - Guinevere_APIIntegration_v2.0.md
  - Guinevere_BRD_v2.0.md
---

# ADR-004: Primary LLM Model Selection

## Status

Accepted

## Date

2026-05-30

## Deciders

Faiz (Owner, solo developer Indonesia); Guinevere (Executor / autonomous system steward)

## Tags

llm, model, 9router, canonical

## Risk Level

HIGH

## Supersedes

N/A

## Related Documents

| Document | Relationship |
|---|---|
| [`../Guinevere_TechnicalArchitecture_v2.0.md`](../Guinevere_TechnicalArchitecture_v2.0.md) | Guinevere_TechnicalArchitecture_v2.0.md |
| [`../Guinevere_APIIntegration_v2.0.md`](../Guinevere_APIIntegration_v2.0.md) | Guinevere_APIIntegration_v2.0.md |
| [`../Guinevere_BRD_v2.0.md`](../Guinevere_BRD_v2.0.md) | Guinevere_BRD_v2.0.md |

## Context

The v2.0 documentation locks the primary Guinevere model as GPT-5.5 via 9Router with a 1M context window. Earlier drafts contained Hermes 3, OpenRouter, and inconsistent context-window assumptions.

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

1. Hermes 3 via 9Router
2. GPT-5.5 via OpenRouter
3. GPT-5.5 via 9Router with 1M context

## Decision Outcome

Chosen option: **GPT-5.5 via 9Router with 1M context**.

Use GPT-5.5 via 9Router as the primary model for Guinevere core reasoning, coding orchestration, persona synthesis, and high-context project work. Treat the 1M context window as a core capability assumption requiring runtime monitoring and fallback-to-queue behavior when unavailable.

## Consequences

### Positive

- Aligns all core docs to one model
- Supports long-context project memory and documentation work
- Reduces routing ambiguity

### Negative

- Strong dependency on GPT-5.5 and 9Router availability
- Cost and latency must be monitored

### Risks

- Provider behavior or context limits may change
- No alternative primary model is approved in this ADR

## Implementation Notes

- Implementation must update the relevant v2.0 source documents or future superseding specs if this ADR changes state.
- Accepted ADRs must not be edited in-place for material decision changes; create a superseding ADR instead.
- Proposed ADRs require Faiz approval before they become binding runtime policy.
- Any sub-agent research, implementation summary, audit, or verification used for this ADR must be written to markdown evidence, not returned only inline.

## Links

- [`../Guinevere_TechnicalArchitecture_v2.0.md`](../Guinevere_TechnicalArchitecture_v2.0.md)
- [`../Guinevere_APIIntegration_v2.0.md`](../Guinevere_APIIntegration_v2.0.md)
- [`../Guinevere_BRD_v2.0.md`](../Guinevere_BRD_v2.0.md)
- [`../Guinevere_ADR_Index_v1.0.md`](../Guinevere_ADR_Index_v1.0.md)
