---
adr: 023
title: "Financial Data Integration Strategy"
status: "Accepted with notes"
date: "2026-05-30"
deciders:
  - "Faiz (Owner, solo developer Indonesia)"
  - "Guinevere (Executor / autonomous system steward)"
tags:
  - financial
  - ewallet
  - data-integration
  - privacy
risk_level: "MEDIUM"
supersedes: "N/A"
related_documents:
  - Guinevere_PRD_v2.0.md
  - Guinevere_APIIntegration_v2.0.md
  - Guinevere_MemorySchema_v2.0.md
  - Guinevere_BRD_v2.0.md
---

# ADR-023: Financial Data Integration Strategy

## Status

Accepted with notes

## Date

2026-05-30

## Deciders

Faiz (Owner, solo developer Indonesia); Guinevere (Executor / autonomous system steward)

## Tags

financial, ewallet, data-integration, privacy

## Risk Level

MEDIUM

## Supersedes

N/A

## Related Documents

| Document | Relationship |
|---|---|
| [`../Guinevere_PRD_v2.0.md`](../Guinevere_PRD_v2.0.md) | Guinevere_PRD_v2.0.md |
| [`../Guinevere_APIIntegration_v2.0.md`](../Guinevere_APIIntegration_v2.0.md) | Guinevere_APIIntegration_v2.0.md |
| [`../Guinevere_MemorySchema_v2.0.md`](../Guinevere_MemorySchema_v2.0.md) | Guinevere_MemorySchema_v2.0.md |
| [`../Guinevere_BRD_v2.0.md`](../Guinevere_BRD_v2.0.md) | Guinevere_BRD_v2.0.md |
| [`../ADR-007-memory-storage-backend-selection.md`](../ADR-007-memory-storage-backend-selection.md) | ADR-007 — Memory Storage Backend Selection |
| [`../ADR-008-memory-encryption-key-management.md`](../ADR-008-memory-encryption-key-management.md) | ADR-008 — Memory Encryption & Key Management |
| [`../ADR-015-secrets-management-strategy.md`](../ADR-015-secrets-management-strategy.md) | ADR-015 — Secrets Management Strategy |
| [`../ADR-024-data-governance-classification-policy.md`](../ADR-024-data-governance-classification-policy.md) | ADR-024 — Data Governance & Classification Policy |
| [`../ADR-010-surveillance-data-retention-policy.md`](../ADR-010-surveillance-data-retention-policy.md) | ADR-010 — Surveillance Data Retention Policy |
| [`../ADR-018-security-architecture-defense-in-depth.md`](../ADR-018-security-architecture-defense-in-depth.md) | ADR-018 — Security Architecture & Defense-in-Depth |

## Context

Guinevere plans financial tracking through e-wallet parsing, transaction memory, predictions, and reports. Financial data is sensitive and easy to misclassify.

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

1. Manual financial notes only
2. Autonomous scraping/parsing without schema
3. Governed financial integration with provenance and correction

## Decision Outcome

Chosen option: **Governed financial integration with provenance and correction**.

Integrate financial data through explicit data-source contracts, normalized schemas, confidence scoring, manual correction flows, and privacy-aware reporting. Guinevere may summarize and predict but must preserve source provenance and avoid irreversible financial action without approval.

## Consequences

### Positive

- Improves trust in financial summaries
- Allows audit and correction
- Reduces risk of wrong predictions

### Negative

- More schema and validation work
- May delay automation

### Risks

- Parsing errors can create wrong financial advice
- Financial logs are sensitive and need strong access control

## Implementation Notes

- Implementation must update the relevant v2.0 source documents or future superseding specs if this ADR changes state.
- Accepted ADRs must not be edited in-place for material decision changes; create a superseding ADR instead.
- Proposed ADRs require Faiz approval before they become binding runtime policy.
- Any sub-agent research, implementation summary, audit, or verification used for this ADR must be written to markdown evidence, not returned only inline.

## Review Record

- **Date:** 2026-05-30
- **Reviewer:** Senior Architect Reviewer / Guinevere
- **Decision:** Accepted with notes
- **Evidence:** Reviewed against Guinevere_PRD_v2.0.md, Guinevere_APIIntegration_v2.0.md, Guinevere_MemorySchema_v2.0.md, Guinevere_BRD_v2.0.md, ADR-007, ADR-008, ADR-015, ADR-024, ADR-010, ADR-018, and batch-2 research reports (2026-05-30-adr-batch2-map.md, 2026-05-30-adr-batch2-consistency.md, 2026-05-30-adr-batch2-technical-sanity.md).
- **Notes:**
  - **Data-source mechanics (exact):**
    - **E-wallet:** Android Tasker notification capture via `NotificationListenerService`. Document Tasker profile/trigger, notification access permission, parsed fields (amount, merchant, timestamp, type), and encrypted transmission to Guinevere (Tailscale-only endpoint per ADR-019). Note: Android 14+ foreground service restrictions require `FOREGROUND_SERVICE_SPECIAL_USE`; battery optimization must be set to "Unrestricted" manually per device.
    - **Bank:** Transaction aggregation via bank API (if available), CSV/statement import, or manual entry. Normalization schema and matching logic must be documented.
    - **Explicit prohibition:** No web scraping of financial sites/apps. Rationale: TOS violation, fragility, PII exposure. PRD v2.0 section 7.1 currently uses "app scraping" terminology; this must be updated to "Tasker AutoNotification capture" to align with ADR-023.
  - **Financial data classification:** Financial data = CRITICAL per ADR-024. Encryption at rest via PostgreSQL pgcrypto or column-level encryption (per ADR-008). Access control: Tailscale-only per ADR-019. Retention policy aligned with ADR-010 but distinct from surveillance "selamanya".
  - **Confidence scoring:** Define confidence per source: Tasker capture = high confidence on amount/merchant, low on category; bank API = variable; CSV import = manual verification required.
  - **Correction flow:** Manual correction UI or command interface. Correction audit trail stored in memory. Corrections propagate to predictions/reports.
  - **Duplicate/deferred/missing handling:** Duplicate detection via transaction ID or amount+timestamp+merchant. Deferred notifications (phone off) may arrive in batches. Missing notifications (Doze mode, force-stop) must be logged as gaps.
  - **Regex adapter maintenance:** Each e-wallet/bank requires a maintained regex adapter. Parsers break silently when notification text changes with app updates or language settings.
  - **Follow-up:** PRD v2.0 section 7.1 requires future wording cleanup from "scraping" to "Tasker notification capture".

## Links

- [`../Guinevere_PRD_v2.0.md`](../Guinevere_PRD_v2.0.md)
- [`../Guinevere_APIIntegration_v2.0.md`](../Guinevere_APIIntegration_v2.0.md)
- [`../Guinevere_MemorySchema_v2.0.md`](../Guinevere_MemorySchema_v2.0.md)
- [`../Guinevere_BRD_v2.0.md`](../Guinevere_BRD_v2.0.md)
- [`../Guinevere_ADR_Index_v1.0.md`](../Guinevere_ADR_Index_v1.0.md)
