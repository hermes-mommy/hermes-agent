---
adr: 003
title: "Persona Drift Control & Validation"
status: "Accepted with notes"
date: "2026-05-30"
deciders:
  - "Faiz (Owner, solo developer Indonesia)"
  - "Guinevere (Executor / autonomous system steward)"
tags:
  - persona
  - drift
  - validation
  - audit
risk_level: "HIGH"
supersedes: "N/A"
related_documents:
  - Guinevere_Persona_Document_v2.0.md
  - Guinevere_MemorySchema_v2.0.md
  - Guinevere_AgentLoopSpec_v2.0.md
---

# ADR-003: Persona Drift Control & Validation

## Status

Accepted with notes

## Date

2026-05-30

## Deciders

Faiz (Owner, solo developer Indonesia); Guinevere (Executor / autonomous system steward)

## Tags

persona, drift, validation, audit

## Risk Level

HIGH

## Supersedes

N/A

## Related Documents

| Document | Relationship |
|---|---|
| [`../Guinevere_Persona_Document_v2.0.md`](../Guinevere_Persona_Document_v2.0.md) | Guinevere_Persona_Document_v2.0.md |
| [`../Guinevere_MemorySchema_v2.0.md`](../Guinevere_MemorySchema_v2.0.md) | Guinevere_MemorySchema_v2.0.md |
| [`../Guinevere_AgentLoopSpec_v2.0.md`](../Guinevere_AgentLoopSpec_v2.0.md) | Guinevere_AgentLoopSpec_v2.0.md |
| [`../ADR-001-persona-safety-ethical-boundary.md`](../ADR-001-persona-safety-ethical-boundary.md) | ADR-001 — Persona Safety & Ethical Boundary Policy |
| [`../ADR-002-user-autonomy-safe-word-enforcement.md`](../ADR-002-user-autonomy-safe-word-enforcement.md) | ADR-002 — User Autonomy & Safe Word Enforcement |
| [`../ADR-008-memory-encryption-key-management.md`](../ADR-008-memory-encryption-key-management.md) | ADR-008 — Memory Encryption & Key Management |
| [`../ADR-012-sub-agent-orchestration-governance.md`](../ADR-012-sub-agent-orchestration-governance.md) | ADR-012 — Sub-Agent Orchestration Governance |
| [`../ADR-024-data-governance-classification-policy.md`](../ADR-024-data-governance-classification-policy.md) | ADR-024 — Data Governance & Classification Policy |

## Context

Guinevere stores emotional events, drift logs, inner journals, and long-term preferences. Without validation, the persona can gradually become harsher, more possessive, or more manipulative than intended.

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

1. Allow autonomous persona evolution without governance
2. Manually review only when Faiz notices issues
3. Create drift logs, validation checks, and rollback/safe-mode rules

## Decision Outcome

Chosen option: **Create drift logs, validation checks, and rollback/safe-mode rules**.

Track persona drift as an auditable runtime concern. Persona changes require drift logs, review criteria, rollback/safe-mode behavior, and periodic validation against canonical persona and safety boundaries.

## Consequences

### Positive

- Makes persona change observable
- Supports rollback after harmful or off-brand behavior
- Connects memory updates with safety validation

### Negative

- Adds operational complexity
- Requires subjective review rubrics

### Risks

- Validation may miss subtle manipulation
- Rollback may conflict with remembered relationship context

## Implementation Notes

- Implementation must update the relevant v2.0 source documents or future superseding specs if this ADR changes state.
- Accepted ADRs must not be edited in-place for material decision changes; create a superseding ADR instead.
- Proposed ADRs require Faiz approval before they become binding runtime policy.
- Any sub-agent research, implementation summary, audit, or verification used for this ADR must be written to markdown evidence, not returned only inline.

## Review Record

- **Date:** 2026-05-30
- **Reviewer:** Senior Architect Reviewer / Guinevere
- **Decision:** Accepted with notes
- **Evidence:** Reviewed against Guinevere_Persona_Document_v2.0.md, Guinevere_MemorySchema_v2.0.md, Guinevere_AgentLoopSpec_v2.0.md, ADR-001, ADR-002, ADR-008, ADR-012, ADR-024, and batch-2 research reports (2026-05-30-adr-batch2-map.md, 2026-05-30-adr-batch2-consistency.md, 2026-05-30-adr-batch2-technical-sanity.md).
- **Notes:**
  - **Rollback mechanism:** Define explicit rollback triggers: (1) automated validation failure (threshold breach), (2) Faiz request, (3) auditor flag. Specify reverted state semantics: restore last known-good persona snapshot from memory, not a hard baseline reset. Safe-mode criteria must be threshold-based with human override.
  - **Safe word interaction:** Rollback must not bypass ADR-002 safe word protections. If safe word is active, rollback defers to safe word state and does not modify persona parameters until safe word is released.
  - **Autonomy vs. approval:** Rollback of persona parameters is autonomous for threshold breaches; Faiz-requested rollback is direct; auditor-flagged rollback requires Faiz approval unless ADR-001 safety boundary is violated.
  - **Drift log schema:** Reference specific table/schema in Guinevere_MemorySchema_v2.0.md (e.g., `persona_drift_logs` with timestamp, drift_vector, trigger, reviewer, action). Align with ADR-024 data classification.
  - **Validation cadence:** Specify per-loop lightweight validation + periodic deep validation (e.g., every 100 interactions or daily). Deep validation uses sub-agent per ADR-012 file-based output rules.
  - **ADR-001 safety rubric:** Map drift categories to ADR-001 boundary categories (distress, coercion, surveillance, punishment, privacy, irreversible action).

## Links

- [`../Guinevere_Persona_Document_v2.0.md`](../Guinevere_Persona_Document_v2.0.md)
- [`../Guinevere_MemorySchema_v2.0.md`](../Guinevere_MemorySchema_v2.0.md)
- [`../Guinevere_AgentLoopSpec_v2.0.md`](../Guinevere_AgentLoopSpec_v2.0.md)
- [`../Guinevere_ADR_Index_v1.0.md`](../Guinevere_ADR_Index_v1.0.md)
