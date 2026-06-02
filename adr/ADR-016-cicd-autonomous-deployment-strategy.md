---
adr: 016
title: "CI/CD & Autonomous Deployment Strategy"
status: "Accepted with notes"
date: "2026-05-30"
deciders:
  - "Faiz (Owner, solo developer Indonesia)"
  - "Guinevere (Executor / autonomous system steward)"
tags:
  - cicd
  - deployment
  - autonomy
  - release
risk_level: "HIGH"
supersedes: "N/A"
related_documents:
  - Guinevere_TechnicalArchitecture_v2.0.md
  - Guinevere_AgentLoopSpec_v2.0.md
  - Guinevere_BRD_v2.0.md
---

# ADR-016: CI/CD & Autonomous Deployment Strategy

## Status

Accepted with notes

## Date

2026-05-30

## Deciders

Faiz (Owner, solo developer Indonesia); Guinevere (Executor / autonomous system steward)

## Tags

cicd, deployment, autonomy, release

## Risk Level

HIGH

## Supersedes

N/A

## Related Documents

| Document | Relationship |
|---|---|
| [`../Guinevere_TechnicalArchitecture_v2.0.md`](../Guinevere_TechnicalArchitecture_v2.0.md) | Guinevere_TechnicalArchitecture_v2.0.md |
| [`../Guinevere_AgentLoopSpec_v2.0.md`](../Guinevere_AgentLoopSpec_v2.0.md) | Guinevere_AgentLoopSpec_v2.0.md |
| [`../Guinevere_BRD_v2.0.md`](../Guinevere_BRD_v2.0.md) | Guinevere_BRD_v2.0.md |
| [`../ADR-013-guinevere-mcp-native-opencode-replacement.md`](../ADR-013-guinevere-mcp-native-opencode-replacement.md) | ADR-013 — Guinevere MCP Native OpenCode Replacement |
| [`../ADR-014-vps-container-architecture.md`](../ADR-014-vps-container-architecture.md) | ADR-014 — VPS & Container Architecture |
| [`../ADR-015-secrets-management-strategy.md`](../ADR-015-secrets-management-strategy.md) | ADR-015 — Secrets Management Strategy |
| [`../ADR-017-monitoring-stack-selection.md`](../ADR-017-monitoring-stack-selection.md) | ADR-017 — Monitoring Stack Selection |
| [`../ADR-012-sub-agent-orchestration-governance.md`](../ADR-012-sub-agent-orchestration-governance.md) | ADR-012 — Sub-Agent Orchestration Governance |

## Context

The architecture includes GitHub Actions, self-deploy behavior, evidence artifacts, and autonomous agent loops. Autonomous deployment is powerful but dangerous without preflight checks, rollback, and approval gates.

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

1. Fully autonomous deploy on every successful loop
2. Manual-only deploy
3. Autonomous preparation with governed deployment gates

## Decision Outcome

Chosen option: **Autonomous preparation with governed deployment gates**.

Adopt CI/CD with explicit preflight verification, evidence capture, rollback path, and human approval requirements for destructive or production-impacting changes. Guinevere may prepare deployments autonomously, but release gates must be policy-driven.

## Consequences

### Positive

- Balances autonomy with safety
- Creates evidence for each release
- Supports future release governance

### Negative

- Slower than pure self-deploy
- Requires maintaining deployment checklists

### Risks

- Bad gate design can either block velocity or allow unsafe deploys
- Rollback must be tested

## Implementation Notes

- Implementation must update the relevant v2.0 source documents or future superseding specs if this ADR changes state.
- Accepted ADRs must not be edited in-place for material decision changes; create a superseding ADR instead.
- Proposed ADRs require Faiz approval before they become binding runtime policy.
- Any sub-agent research, implementation summary, audit, or verification used for this ADR must be written to markdown evidence, not returned only inline.

## Review Record

- **Date:** 2026-05-30
- **Reviewer:** Senior Architect Reviewer / Guinevere
- **Decision:** Accepted with notes
- **Evidence:** Reviewed against Guinevere_TechnicalArchitecture_v2.0.md, Guinevere_AgentLoopSpec_v2.0.md, Guinevere_BRD_v2.0.md, ADR-011, ADR-013, ADR-014, ADR-015, ADR-017, ADR-012, and batch-2 research reports (2026-05-30-adr-batch2-map.md, 2026-05-30-adr-batch2-consistency.md, 2026-05-30-adr-batch2-technical-sanity.md).
- **Notes:**
  - **CD mechanism:** Self-deploy via cron + git pull on primary VPS only. GitHub Actions is used for CI exclusively (lint, test, security scan). No GitHub Actions workflow triggers production deployment. Cost rationale: runner-minute charges vs. zero-cost self-deploy.
  - **Deploy script:** Document exact script: `git fetch && git reset --hard origin/main && uv sync && pytest && systemctl restart <service>`. Use `fetch + reset --hard` semantics to handle merge conflicts; discard local changes unconditionally.
  - **Preflight checklist:** Gate on tests passing, secrets valid (SOPS decryption per ADR-015), container image digest verified, evidence artifact generated under `evidence/<scope>/<artifact-name>.md` per ADR-012 conventions.
  - **Health check + rollback:** Post-deploy health check must verify Prometheus/Grafana availability (ADR-017). Rollback requires exercising in staging before first production deploy. No automated rollback in cron script; manual `git revert` + restart.
  - **Secret storage:** `DEPLOY_SSH_KEY` stored on server (systemd credential or file). Different trust boundary than GitHub Actions secrets; rotation is manual per ADR-015.
  - **Logging:** Use systemd timer over cron for journald integration and `Persistent=true` catch-up on reboot.

## Links

- [`../Guinevere_TechnicalArchitecture_v2.0.md`](../Guinevere_TechnicalArchitecture_v2.0.md)
- [`../Guinevere_AgentLoopSpec_v2.0.md`](../Guinevere_AgentLoopSpec_v2.0.md)
- [`../Guinevere_BRD_v2.0.md`](../Guinevere_BRD_v2.0.md)
- [`../Guinevere_ADR_Index_v1.0.md`](../Guinevere_ADR_Index_v1.0.md)
