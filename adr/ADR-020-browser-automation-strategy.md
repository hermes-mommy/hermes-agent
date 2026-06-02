---
adr: 020
title: "Browser Automation Strategy"
status: "Accepted"
date: "2026-05-30"
deciders:
  - "Faiz (Owner, solo developer Indonesia)"
  - "Guinevere (Executor / autonomous system steward)"
tags:
  - browser
  - obscura
  - playwright
  - automation
risk_level: "MEDIUM"
supersedes: "N/A"
related_documents:
  - Guinevere_APIIntegration_v2.0.md
  - Guinevere_TechnicalArchitecture_v2.0.md
  - Guinevere_AgentLoopSpec_v2.0.md
---

# ADR-020: Browser Automation Strategy

## Status

Accepted

## Date

2026-05-30

## Deciders

Faiz (Owner, solo developer Indonesia); Guinevere (Executor / autonomous system steward)

## Tags

browser, obscura, playwright, automation

## Risk Level

MEDIUM

## Supersedes

N/A

## Related Documents

| Document | Relationship |
|---|---|
| [`../Guinevere_APIIntegration_v2.0.md`](../Guinevere_APIIntegration_v2.0.md) | Guinevere_APIIntegration_v2.0.md |
| [`../Guinevere_TechnicalArchitecture_v2.0.md`](../Guinevere_TechnicalArchitecture_v2.0.md) | Guinevere_TechnicalArchitecture_v2.0.md |
| [`../Guinevere_AgentLoopSpec_v2.0.md`](../Guinevere_AgentLoopSpec_v2.0.md) | Guinevere_AgentLoopSpec_v2.0.md |

## Context

Canonical decisions state browser automation uses obscura as the primary path and Playwright as fallback. Earlier docs mentioned browser MCP inconsistently.

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

1. Browser MCP as primary
2. Playwright only
3. obscura primary with Playwright fallback

## Decision Outcome

Chosen option: **obscura primary with Playwright fallback**.

Use obscura as the primary browser automation layer for Guinevere tasks and Playwright as fallback for validation, deterministic browser testing, and compatibility gaps.

## Consequences

### Positive

- Clarifies tool hierarchy
- Keeps Playwright available for reliable verification
- Avoids inconsistent browser MCP references

### Negative

- Two browser paths require clear routing rules
- obscura maturity must be monitored

### Risks

- Browser automation can expose credentials or private pages
- Fallback mismatch can produce different behavior

## Implementation Notes

- Implementation must update the relevant v2.0 source documents or future superseding specs if this ADR changes state.
- Accepted ADRs must not be edited in-place for material decision changes; create a superseding ADR instead.
- Proposed ADRs require Faiz approval before they become binding runtime policy.
- Any sub-agent research, implementation summary, audit, or verification used for this ADR must be written to markdown evidence, not returned only inline.

## Links

- [`../Guinevere_APIIntegration_v2.0.md`](../Guinevere_APIIntegration_v2.0.md)
- [`../Guinevere_TechnicalArchitecture_v2.0.md`](../Guinevere_TechnicalArchitecture_v2.0.md)
- [`../Guinevere_AgentLoopSpec_v2.0.md`](../Guinevere_AgentLoopSpec_v2.0.md)
- [`../Guinevere_ADR_Index_v1.0.md`](../Guinevere_ADR_Index_v1.0.md)
