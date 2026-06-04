---
adr: 022
title: "Communication Channel Strategy"
status: "Accepted with notes (Revised 2026-06-03)"
date: "2026-05-30"
deciders:
  - "Faiz (Owner, solo developer Indonesia)"
  - "Guinevere (Executor / autonomous system steward)"
tags:
  - discord
  - whatsapp
  - email
  - communication
risk_level: "HIGH"
supersedes: "N/A"
related_documents:
  - Guinevere_PRD_v2.0.md
  - Guinevere_APIIntegration_v2.0.md
  - Guinevere_TechnicalArchitecture_v2.0.md
---

# ADR-022: Communication Channel Strategy

## Status

Accepted with notes (Revised 2026-06-03)

## Date

2026-05-30

## Deciders

Faiz (Owner, solo developer Indonesia); Guinevere (Executor / autonomous system steward)

## Tags

discord, whatsapp, email, communication

## Risk Level

HIGH

## Supersedes

N/A

## Related Documents

| Document | Relationship |
|---|---|
| [`../Guinevere_PRD_v2.0.md`](../Guinevere_PRD_v2.0.md) | Guinevere_PRD_v2.0.md |
| [`../Guinevere_APIIntegration_v2.0.md`](../Guinevere_APIIntegration_v2.0.md) | Guinevere_APIIntegration_v2.0.md |
| [`../Guinevere_TechnicalArchitecture_v2.0.md`](../Guinevere_TechnicalArchitecture_v2.0.md) | Guinevere_TechnicalArchitecture_v2.0.md |
| [`../ADR-001-persona-safety-ethical-boundary.md`](../ADR-001-persona-safety-ethical-boundary.md) | ADR-001 — Persona Safety & Ethical Boundary Policy |
| [`../ADR-002-user-autonomy-safe-word-enforcement.md`](../ADR-002-user-autonomy-safe-word-enforcement.md) | ADR-002 — User Autonomy & Safe Word Enforcement |
| [`../ADR-010-surveillance-data-retention-policy.md`](../ADR-010-surveillance-data-retention-policy.md) | ADR-010 — Surveillance Data Retention Policy |
| [`../ADR-024-data-governance-classification-policy.md`](../ADR-024-data-governance-classification-policy.md) | ADR-024 — Data Governance & Classification Policy |
| [`../ADR-018-security-architecture-defense-in-depth.md`](../ADR-018-security-architecture-defense-in-depth.md) | ADR-018 — Security Architecture & Defense-in-Depth |
| [`../ADR-021-wearable-integration-post-mvp.md`](../ADR-021-wearable-integration-post-mvp.md) | ADR-021 — Wearable Integration Post-MVP |

## Context

Guinevere uses Discord as a primary interface and may integrate WhatsApp, email, Gotify/FCM, GitHub, and other communication channels. Channel purpose and disclosure boundaries need governance.

This ADR is part of the first Guinevere technical-core ADR batch and inherits these locked project decisions unless explicitly stated otherwise:

- Primary LLM is GPT-5.5 via 9Router with 1M context window.
- Sub-agent LLM is DeepSeek V4 Flash via 9Router.
- All LLM routing goes through 9Router; OpenRouter is not a fallback path.
- Memory uses PostgreSQL primary storage plus Redis cache; SQLite is excluded.
- Autonomous SDLC uses exactly 7 phases: Research; Plan & Delegate; Delegate; Execute; Validate & Audit; Update Documents; Setup Evidence.
- Guinevere MCP native fully replaces OpenCode/opencode for the project coding substrate.
- Prometheus + Grafana run on the primary VPS first.
- Wearable integrations are Expansion and must not be treated as active dependencies.
- Browser automation uses obscura as primary and Playwright as fallback.

## Decision Drivers

- Canonical v2.0 documentation must remain internally consistent.
- Faiz is the sole owner and final approver; Guinevere may propose and execute but not silently change accepted decisions.
- Safety, consent, privacy, and recoverability outrank persona flavor and automation speed.
- The decision must be auditable through file-based evidence and linked source documents.

## Considered Options

1. All channels equal
2. Discord only forever
3. Discord primary with governed secondary channels

## Decision Outcome

Chosen option: **Discord primary with governed secondary channels**.

Use Discord as the primary control/chat interface, with WhatsApp/email/notifications as scoped integration channels. Each channel must define purpose, authentication, logging, consent/disclosure, rate limits, and failure behavior before production use.

## Consequences

### Positive

- Clarifies UX ownership
- Reduces accidental cross-channel leakage
- Supports future client communication governance

### Negative

- Secondary integrations need per-channel contracts
- Some automation may wait for policy

### Risks

- WhatsApp/client automation can create disclosure and consent issues
- Notification spam can harm usability

## Implementation Notes

- Implementation must update the relevant v2.0 source documents or future superseding specs if this ADR changes state.
- Accepted ADRs must not be edited in-place for material decision changes; create a superseding ADR instead. (Exception: this ADR was revised in-place on 2026-06-03 per Faiz explicit instruction, with full revision history appended.)
- Proposed ADRs require Faiz approval before they become binding runtime policy.
- Any sub-agent research, implementation summary, audit, or verification used for this ADR must be written to markdown evidence, not returned only inline.

## Review Record

- **Date:** 2026-05-30
- **Reviewer:** Senior Architect Reviewer / Guinevere
- **Decision:** Accepted with notes
- **Evidence:** Reviewed against Guinevere_PRD_v2.0.md, Guinevere_APIIntegration_v2.0.md, Guinevere_TechnicalArchitecture_v2.0.md, ADR-001, ADR-002, ADR-010, ADR-024, ADR-018, ADR-021, and batch-2 research reports (2026-05-30-adr-batch2-map.md, 2026-05-30-adr-batch2-consistency.md, 2026-05-30-adr-batch2-technical-sanity.md).
- **Notes:**
  - **Channel stack (exact):**
    - **Primary:** Discord (control/chat interface, auth via Discord OAuth2/bot token).
    - **WhatsApp:** via Neonize (pure Python, wraps whatsmeow via CGo). Session persistence via PostgreSQL (neonize_postgres backend). Rate limits per WhatsApp TOS. Ban risk <2%/year for reactive-only usage. Protocol breaks every 2-8 weeks; monitor upstream releases.
    - **Email:** Gmail API (OAuth2, read + send scopes) + Resend (transactional outbound fallback).
    - **Push notifications:** Gotify as self-hosted backup notification channel.
  - **Per-channel contract:** Each channel must define purpose, authentication mechanism, logging scope, consent/disclosure boundary, rate limits, failure behavior, and fallback chain before production use.
  - **Identity binding:** Cross-channel identity binding must be documented: how Faiz authenticates across Discord/WhatsApp/Email/Gotify (shared identity token or per-channel).
  - **Disclosure governance:** Reference ADR-024 (Data Governance & Classification) for message content classification. Reference ADR-029 (Consent & Revocation — backlog) for consent flows.
  - **Safe word across channels:** ADR-002 safe word must work identically across all channels. Safe-word activation pauses persona escalation on every channel simultaneously.
  - **Neonize caveats:** v0.3.18.post0 (May 2026, Apache 2.0); pin version in requirements.txt. Pure Python asyncio-native (NewAClient). 45 event types, 49 exception classes. No reconnection tuning exposed to Python — implement exponential backoff wrapper (3 retries, 1s/2s/4s). FFmpeg required for media handling. Session storage: PostgreSQL only (no Redis support). Single Python process — eliminates Node.js bridge entirely.
  - **Gmail/Resend caveats:** Gmail push notifications expire every 7 days; cron/systemd timer must re-establish watch. Gmail 429 errors can persist for hours; implement exponential backoff. Resend rate limit: 5 req/sec default; bounce rate must stay under 4%; spam rate under 0.08%.
  - **Gotify caveats:** Self-hosted; operator handles updates, backups (Docker volumes), TLS termination. No iOS native app; web push on iOS limited.

## Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-05-30 | Faiz + Guinevere | Initial ADR — WhatsApp via Baileys (Node.js, WhatsApp Web MD protocol), separate systemd unit, Node.js bridge. |
| 1.1 | 2026-06-03 | Faiz + Guinevere | Revised WhatsApp implementation from Baileys (Node.js) to Neonize (pure Python, wraps whatsmeow via CGo). Rationale: eliminates Node.js subprocess bridge, single Python process, native asyncio, pip-installable. Session storage corrected from Redis to PostgreSQL (Neonize has no Redis backend). Consequences: positive — reduced process count, no bridge latency, native async; negative — smaller community (399★ vs 8K+), less battle-tested. Rollback: Baileys remains viable fallback via Evolution API (8.4K★, Docker sidecar). |

## Links

- [`../Guinevere_PRD_v2.0.md`](../Guinevere_PRD_v2.0.md)
- [`../Guinevere_APIIntegration_v2.0.md`](../Guinevere_APIIntegration_v2.0.md)
- [`../Guinevere_TechnicalArchitecture_v2.0.md`](../Guinevere_TechnicalArchitecture_v2.0.md)
- [`../Guinevere_ADR_Index_v1.0.md`](../Guinevere_ADR_Index_v1.0.md)
