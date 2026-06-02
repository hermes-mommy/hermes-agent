---
adr: 019
title: "Access Control & VPN Mesh Strategy"
status: "Accepted with notes"
date: "2026-05-30"
deciders:
  - "Faiz (Owner, solo developer Indonesia)"
  - "Guinevere (Executor / autonomous system steward)"
tags:
  - access-control
  - tailscale
  - vpn
  - rbac
risk_level: "HIGH"
supersedes: "N/A"
related_documents:
  - Guinevere_TechnicalArchitecture_v2.0.md
  - Guinevere_APIIntegration_v2.0.md
  - Guinevere_MemorySchema_v2.0.md
---

# ADR-019: Access Control & VPN Mesh Strategy

## Status

Accepted with notes

## Date

2026-05-30

## Deciders

Faiz (Owner, solo developer Indonesia); Guinevere (Executor / autonomous system steward)

## Tags

access-control, tailscale, vpn, rbac

## Risk Level

HIGH

## Supersedes

N/A

## Related Documents

| Document | Relationship |
|---|---|
| [`../Guinevere_TechnicalArchitecture_v2.0.md`](../Guinevere_TechnicalArchitecture_v2.0.md) | Guinevere_TechnicalArchitecture_v2.0.md |
| [`../Guinevere_APIIntegration_v2.0.md`](../Guinevere_APIIntegration_v2.0.md) | Guinevere_APIIntegration_v2.0.md |
| [`../Guinevere_MemorySchema_v2.0.md`](../Guinevere_MemorySchema_v2.0.md) | Guinevere_MemorySchema_v2.0.md |
| [`../ADR-014-vps-container-architecture.md`](../ADR-014-vps-container-architecture.md) | ADR-014 — VPS & Container Architecture |
| [`../ADR-018-security-architecture-defense-in-depth.md`](../ADR-018-security-architecture-defense-in-depth.md) | ADR-018 — Security Architecture & Defense-in-Depth |
| [`../ADR-015-secrets-management-strategy.md`](../ADR-015-secrets-management-strategy.md) | ADR-015 — Secrets Management Strategy |
| [`../ADR-008-memory-encryption-key-management.md`](../ADR-008-memory-encryption-key-management.md) | ADR-008 — Memory Encryption & Key Management |
| [`../ADR-024-data-governance-classification-policy.md`](../ADR-024-data-governance-classification-policy.md) | ADR-024 — Data Governance & Classification Policy |

## Context

The architecture uses Tailscale mesh with zero public ports on the VPS. All devices (Faiz workstations, mobile, VPS) join the tailnet. Internal services are accessed via Tailscale-internal addresses only. Even in a single-user system, services and agents need scoped access.

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

1. Expose admin services publicly with passwords
2. Use VPN-only for everything
3. Use VPN-first admin access with controlled public endpoints

## Decision Outcome

Chosen option: **Use Tailscale mesh for all devices with zero public ports**.

Use Tailscale mesh for all administrative and service surfaces. No public ports are opened on the VPS or routers. Public integrations (Discord, GitHub, 9Router) use outbound/external provider channels or Tailscale-internal routes only. Define service-level access roles even before full RBAC/ABAC exists.

## Consequences

### Positive

- Reduces public attack surface
- Keeps operations manageable
- Prepares for formal RBAC/ABAC

### Negative

- VPN misconfiguration can lock out access
- DERP relay fallback throttles throughput (30–100 Mbps) when direct WireGuard cannot be established

### Risks

- Auth key expiry (default 180 days) can lock out headless nodes if not renewed
- Tailscale control plane is US-hosted; metadata (connection graph, not content) processed on AWS US
- Single-user assumptions may break if clients/users are added

## Implementation Notes

- Implementation must update the relevant v2.0 source documents or future superseding specs if this ADR changes state.
- Accepted ADRs must not be edited in-place for material decision changes; create a superseding ADR instead.
- Proposed ADRs require Faiz approval before they become binding runtime policy.
- Any sub-agent research, implementation summary, audit, or verification used for this ADR must be written to markdown evidence, not returned only inline.

## Review Record

- **Date:** 2026-05-30
- **Reviewer:** Senior Architect Reviewer / Guinevere
- **Decision:** Accepted with notes
- **Evidence:** Reviewed against Guinevere_TechnicalArchitecture_v2.0.md, Guinevere_APIIntegration_v2.0.md, Guinevere_MemorySchema_v2.0.md, ADR-014, ADR-018, ADR-015, ADR-008, ADR-024, and batch-2 research reports (2026-05-30-adr-batch2-map.md, 2026-05-30-adr-batch2-consistency.md, 2026-05-30-adr-batch2-technical-sanity.md).
- **Notes:**
  - **Zero public ports:** All VPS admin surfaces are Tailscale-internal only. Public integrations (Discord, GitHub) use outbound/external provider channels. No public VPS ingress is permitted. This reframes the original Option 3 "controlled public endpoints" to align with ADR-014 and ADR-018 zero-public-ports decisions.
  - **Tailscale ACL:** Document ACL policy file structure with device tags (e.g., `tag:admin`, `tag:service`) and auto-approvers.
  - **Auth key expiry:** Device keys expire after 180 days by default. Headless nodes (VPS) require an auth key with appropriate expiry settings or disabled expiry. Document renewal procedure and offline backup of recovery auth key.
  - **Lockout recovery:** Emergency access path if VPN misconfiguration locks out access: VPS console (cloud provider), Tailscale recovery auth key stored offline, or DERP relay fallback.
  - **DERP/Control plane caveats:** DERP relay fallback throttles to 30–100 Mbps when direct WireGuard cannot be established. Control plane is US-hosted (AWS); metadata (who connects to whom, not content) is processed there. No EU region is selectable as of May 2026. Headscale is a community alternative with maintenance burden.
  - **Subnet routing:** Tailscale does not bypass cloud security groups or host firewalls. Security group rules must allow inbound from Tailscale subnet router IPs.
  - **Overlapping CIDRs:** Plan non-overlapping subnets across all tailnet members to avoid routing conflicts.

## Links

- [`../Guinevere_TechnicalArchitecture_v2.0.md`](../Guinevere_TechnicalArchitecture_v2.0.md)
- [`../Guinevere_APIIntegration_v2.0.md`](../Guinevere_APIIntegration_v2.0.md)
- [`../Guinevere_MemorySchema_v2.0.md`](../Guinevere_MemorySchema_v2.0.md)
- [`../Guinevere_ADR_Index_v1.0.md`](../Guinevere_ADR_Index_v1.0.md)
