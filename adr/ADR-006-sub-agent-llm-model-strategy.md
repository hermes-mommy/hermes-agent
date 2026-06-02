---
adr: 006
title: "Sub-Agent LLM Model Strategy"
status: "Accepted"
date: "2026-05-30"
deciders:
  - "Faiz (Owner, solo developer Indonesia)"
  - "Guinevere (Executor / autonomous system steward)"
tags:
  - llm
  - sub-agent
  - deepseek
  - 9router
risk_level: "MEDIUM"
supersedes: "N/A"
related_documents:
  - Guinevere_AgentLoopSpec_v2.0.md
  - Guinevere_TechnicalArchitecture_v2.0.md
  - Guinevere_APIIntegration_v2.0.md
---

# ADR-006: Sub-Agent LLM Model Strategy

## Status

Accepted

## Date

2026-05-30

## Deciders

Faiz (Owner, solo developer Indonesia); Guinevere (Executor / autonomous system steward)

## Tags

llm, sub-agent, deepseek, 9router

## Risk Level

MEDIUM

## Supersedes

N/A

## Related Documents

| Document | Relationship |
|---|---|
| [`../Guinevere_AgentLoopSpec_v2.0.md`](../Guinevere_AgentLoopSpec_v2.0.md) | Guinevere_AgentLoopSpec_v2.0.md |
| [`../Guinevere_TechnicalArchitecture_v2.0.md`](../Guinevere_TechnicalArchitecture_v2.0.md) | Guinevere_TechnicalArchitecture_v2.0.md |
| [`../Guinevere_APIIntegration_v2.0.md`](../Guinevere_APIIntegration_v2.0.md) | Guinevere_APIIntegration_v2.0.md |

## Context

Guinevere relies on delegated agents for research, audits, implementation support, and verification. The canonical model for sub-agents is DeepSeek V4 Flash via 9Router.

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

1. Use GPT-5.5 for every sub-agent
2. Use mixed ad hoc provider models
3. Use DeepSeek V4 Flash via 9Router as default sub-agent model

## Decision Outcome

Chosen option: **Use DeepSeek V4 Flash via 9Router as default sub-agent model**.

Use DeepSeek V4 Flash via 9Router as the default sub-agent model for background research, audits, implementation summaries, and non-primary delegated reasoning. Primary-model escalation remains reserved for high-risk decisions or final synthesis.

## Consequences

### Positive

- Controls cost for parallel work
- Preserves GPT-5.5 for core synthesis
- Standardizes sub-agent behavior

### Negative

- Sub-agent quality may vary from primary model
- Requires parent verification of all sub-agent outputs

### Risks

- Low-cost model mistakes can propagate if parent skips verification
- Model changes through 9Router need re-validation

## Implementation Notes

- Implementation must update the relevant v2.0 source documents or future superseding specs if this ADR changes state.
- Accepted ADRs must not be edited in-place for material decision changes; create a superseding ADR instead.
- Proposed ADRs require Faiz approval before they become binding runtime policy.
- Any sub-agent research, implementation summary, audit, or verification used for this ADR must be written to markdown evidence, not returned only inline.

## Links

- [`../Guinevere_AgentLoopSpec_v2.0.md`](../Guinevere_AgentLoopSpec_v2.0.md)
- [`../Guinevere_TechnicalArchitecture_v2.0.md`](../Guinevere_TechnicalArchitecture_v2.0.md)
- [`../Guinevere_APIIntegration_v2.0.md`](../Guinevere_APIIntegration_v2.0.md)
- [`../Guinevere_ADR_Index_v1.0.md`](../Guinevere_ADR_Index_v1.0.md)
