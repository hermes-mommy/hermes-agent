---
adr: 029
title: "Self-Modification Automated Testing"
status: "Accepted"
date: "2026-05-30"
deciders:
  - "Faiz (Owner, solo developer Indonesia)"
  - "Guinevere (Executor / autonomous system steward)"
tags:
  - self-modification
  - testing
  - rollback
  - safety
  - autonomy
risk_level: "CRITICAL"
supersedes: "N/A"
related_documents:
  - adr/ADR-016-cicd-autonomous-deployment-strategy.md
  - Guinevere_AgentLoopSpec_v2.0.md
  - adr/ADR-001-persona-safety-ethical-boundary.md
---

# ADR-029: Self-Modification Automated Testing

## Status

Accepted

## Date

2026-05-30

## Deciders

Faiz (Owner, solo developer Indonesia); Guinevere (Executor / autonomous system steward)

## Tags

self-modification, testing, rollback, safety, autonomy

## Risk Level

CRITICAL

## Supersedes

N/A

## Related Documents

| Document | Relationship |
|---|---|
| [`ADR-016`](ADR-016-cicd-autonomous-deployment-strategy.md) | CI/CD and autonomous deployment strategy |
| [`../Guinevere_AgentLoopSpec_v2.0.md`](../Guinevere_AgentLoopSpec_v2.0.md) | Autonomous SDLC loop specification |
| [`ADR-001`](ADR-001-persona-safety-ethical-boundary.md) | Persona safety and ethical boundary policy |

## Context

Guinevere modifies her own code through the autonomous SDLC loop defined in the AgentLoopSpec. Self-modification without safeguards risks breaking the running system, introducing safety violations, corrupting memory pipelines, or silently altering persona and safety boundaries.

The authority hierarchy for Guinevere operations, confirmed by the operator (Faiz), is: **safety > user > policy**. This means safety boundaries always take precedence over user requests, which in turn take precedence over internal policy defaults.

The SDLC loop enables Guinevere to research, plan, execute, validate, and deploy code changes autonomously. Without mandatory automated testing gates, a self-modification cycle could deploy changes that:

- Break core services or database connectivity
- Introduce persona drift or safety boundary violations
- Corrupt memory encryption or surveillance pipelines
- Create unrecoverable system states

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

- Self-modification must never compromise system stability or safety boundaries.
- Authority hierarchy (safety > user > policy) must be enforced programmatically.
- Failed changes must be automatically reversible without human intervention.
- Routine, low-risk changes should deploy autonomously to maintain development velocity.
- Safety-critical changes require human review regardless of test results.
- The testing gate must not be bypassed by any autonomous process.

## Considered Options

1. Human-only review for all self-modifications
2. No automated testing — trust SDLC validation phase alone
3. Sandbox-only execution without production deployment
4. Automated testing with safety-gated human review and automatic rollback

## Decision Outcome

Chosen option: **Automated testing with safety-gated human review and automatic rollback**.

All Guinevere self-modification MUST pass automated testing before deployment to production. The testing gate enforces the following rules:

### Automatic Rollback

- If any automated test fails after deployment, the system performs an automatic `git revert` to the last known-good commit.
- Rollback must complete within 60 seconds and restore full service operation.
- Rollback events are logged and alerted Faiz for review.

### Safety-Critical Change Classification

Changes touching the following areas are classified as safety-critical and require explicit Faiz review before deployment, regardless of test results:

- Persona behavior, tone, or mood model code
- Safety boundary enforcement or safe-word handling
- Surveillance data collection, retention, or processing
- Encryption, key management, or secrets handling
- Memory access control or privacy-related logic
- Autonomous loop phase transitions or governance rules

### Routine Change Auto-Deployment

Changes that do not touch safety-critical areas may auto-deploy if:

- All unit tests pass
- All integration tests pass
- No regression in existing test coverage
- The change does not modify safety, persona, surveillance, or encryption files

### Authority Hierarchy Enforcement

The authority hierarchy (safety > user > policy) is enforced as a hard constraint:

- No self-modification may weaken safety boundaries even if requested by the user.
- User-level preferences override policy defaults but not safety constraints.
- Policy-level changes (non-safety, non-user-preference) may auto-deploy with tests passing.

## Consequences

### Positive

- Prevents unsafe self-modifications from reaching production
- Automatic rollback ensures rapid recovery from failed deployments
- Safety-critical changes always receive human review
- Routine changes maintain autonomous development velocity
- Authority hierarchy is programmatically enforced, not just documented

### Negative

- Safety-critical classification adds overhead to persona, safety, and surveillance development
- Test suite must be comprehensive and well-maintained to be effective
- False positives in safety-critical classification may slow legitimate changes
- Automatic rollback could mask intermittent issues if not properly investigated

### Risks

- Incomplete test coverage could allow unsafe changes to pass automated testing
- Safety-critical file classification must be kept up to date as the codebase evolves
- Git rollback assumes a clean commit history; merge conflicts could complicate recovery
- A determined self-modification loop could theoretically attempt to weaken the testing gate itself (mitigated by classifying testing infrastructure as safety-critical)

## Implementation Notes

- Automated testing must run as part of the SDLC loop Validate & Audit phase before any deployment.
- Test categories: unit tests, integration tests, safety boundary tests, and regression tests.
- Safety-critical file paths must be defined in a configuration file (e.g., `.guinevere/safety-critical-paths.yml`) and treated as safety-critical themselves.
- The `git revert` rollback mechanism must be tested regularly to ensure reliability.
- Rollback events must generate alerts via Discord (ADR-022) and log to the audit trail.
- The testing gate configuration and enforcement logic are themselves safety-critical and require Faiz review to modify.
- Implementation must update the relevant v2.0 source documents or future superseding specs if this ADR changes state.
- Accepted ADRs must not be edited in-place for material decision changes; create a superseding ADR instead.
- Proposed ADRs require Faiz approval before they become binding runtime policy.
- Any sub-agent research, implementation summary, audit, or verification used for this ADR must be written to markdown evidence, not returned only inline.

## Links

- [`ADR-016`](ADR-016-cicd-autonomous-deployment-strategy.md)
- [`ADR-001`](ADR-001-persona-safety-ethical-boundary.md)
- [`../Guinevere_AgentLoopSpec_v2.0.md`](../Guinevere_AgentLoopSpec_v2.0.md)
- [`../Guinevere_Persona_Document_v2.0.md`](../Guinevere_Persona_Document_v2.0.md)
- [`../Guinevere_ADR_Index_v1.0.md`](../Guinevere_ADR_Index_v1.0.md)
