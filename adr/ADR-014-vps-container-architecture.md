---
adr: 014
title: "VPS & Container Architecture"
status: "Accepted"
date: "2026-05-30"
deciders:
  - "Faiz (Owner, solo developer Indonesia)"
  - "Guinevere (Executor / autonomous system steward)"
tags:
  - infrastructure
  - vps
  - docker
  - ubuntu
risk_level: "HIGH"
supersedes: "N/A"
related_documents:
  - Guinevere_TechnicalArchitecture_v2.0.md
  - Guinevere_APIIntegration_v2.0.md
  - Guinevere_BRD_v2.0.md
---

# ADR-014: VPS & Container Architecture

## Status

Accepted

## Date

2026-05-30

## Deciders

Faiz (Owner, solo developer Indonesia); Guinevere (Executor / autonomous system steward)

## Tags

infrastructure, vps, docker, ubuntu

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

Guinevere runs on Ubuntu 24.04 VPS hosted at hostdata.id with Python 3.12, FastAPI, PostgreSQL, Redis, systemd services, and selected Dockerized components.

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

1. Local-only workstation deployment
2. Kubernetes from day one
3. Single primary VPS with systemd and selective containers

## Decision Outcome

Chosen option: **Single primary VPS with systemd and selective containers**.

Use a primary Ubuntu 24.04 VPS deployment with systemd-managed Guinevere services and containerized supporting services where appropriate. Treat the deployment as Guinevere-focused and isolate unrelated tenants through future ADRs if required.

## Consequences

### Positive

- Matches solo-developer operational capacity
- Keeps infrastructure understandable
- Supports 24/7 autonomous operation

### Negative

- Single VPS is a major availability boundary
- Manual ops discipline is required

### Risks

- Resource saturation can affect all services
- Future scale-out requires migration planning

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
