---
adr: 026
title: "Public Endpoint via Cloudflare Tunnel"
status: "Accepted"
date: "2026-05-30"
deciders:
  - "Faiz (Owner, solo developer Indonesia)"
  - "Guinevere (Executor / autonomous system steward)"
tags:
  - network
  - cloudflare
  - tunnel
  - webhook
  - discord
  - public-endpoint
risk_level: "MEDIUM"
supersedes: "N/A"
related_documents:
  - Guinevere_TechnicalArchitecture_v2.0.md
  - ADR-019-access-control-vpn-mesh-strategy.md
  - Guinevere_APIIntegration_v2.0.md
---

# ADR-026: Public Endpoint via Cloudflare Tunnel

## Status

Accepted

## Date

2026-05-30

## Deciders

Faiz (Owner, solo developer Indonesia); Guinevere (Executor / autonomous system steward)

## Tags

network, cloudflare, tunnel, webhook, discord, public-endpoint

## Risk Level

MEDIUM

## Supersedes

N/A

## Related Documents

| Document | Relationship |
|---|---|
| [`../Guinevere_TechnicalArchitecture_v2.0.md`](../Guinevere_TechnicalArchitecture_v2.0.md) | Defines VPS topology, network architecture, and service exposure policy |
| [`./ADR-019-access-control-vpn-mesh-strategy.md`](./ADR-019-access-control-vpn-mesh-strategy.md) | Establishes Tailscale as primary access network; ADR-026 adds the sole public exception |
| [`../Guinevere_APIIntegration_v2.0.md`](../Guinevere_APIIntegration_v2.0.md) | Discord webhook integration requirements |

## Context

Guinevere requires at least one public endpoint to receive Discord webhook events. Without a public endpoint, Discord cannot deliver webhook payloads to Guinevere, breaking the Discord communication channel strategy (ADR-022).

The 210-question feasibility assessment established that the operator explicitly confirmed a minimum of one public endpoint must exist (Q-series on network exposure). However, the security-first design (ADR-018, ADR-019) mandates that all other services remain private, accessible only via Tailscale mesh.

This ADR resolves how to expose exactly one endpoint publicly while maintaining the defense-in-depth posture defined in the security and access control ADRs.

## Decision Drivers

- Canonical v2.0 documentation must remain internally consistent.
- Faiz is the sole owner and final approver; Guinevere may propose and execute but not silently change accepted decisions.
- Safety, consent, privacy, and recoverability outrank persona flavor and automation speed.
- The decision must be auditable through file-based evidence and linked source documents.
- Discord webhook delivery requires a public endpoint; no alternative mechanism exists for push-based webhooks.

## Considered Options

1. Direct VPS public IP exposure (open firewall port)
2. ngrok or similar dynamic tunnel service
3. Cloudflare Tunnel (cloudflared) for minimal endpoint exposure

## Decision Outcome

Chosen option: **Cloudflare Tunnel (cloudflared) for minimal endpoint exposure**.

Use Cloudflare Tunnel to expose only the Discord webhook endpoint to the public internet. All other Guinevere services remain private, accessible only via Tailscale mesh network (ADR-019). Cloudflare Tunnel runs as a systemd service on the primary VPS. The free tier is sufficient for a single webhook endpoint.

## Consequences

### Positive

- Discord webhook events can be received without exposing the VPS IP directly
- Only one endpoint is exposed; all other services remain private
- Cloudflare provides DDoS protection and TLS termination
- Free tier sufficient for single webhook endpoint
- Tailscale remains the primary access method for all other operations (ADR-019)
- No need to manage SSL certificates manually (Cloudflare handles TLS)

### Negative

- Adds a dependency on Cloudflare infrastructure
- Requires monitoring the tunnel service for failures
- Exposes one endpoint to the public internet, increasing attack surface (though mitigated by Cloudflare)

### Risks

- Tunnel misconfiguration could expose unintended services
- Cloudflare outage blocks Discord webhook delivery
- Tunnel credentials must be stored securely (ADR-015)
- Rate limiting and abuse protection must be configured at the application layer

## Implementation Notes

- Deploy `cloudflared` as a systemd service on the primary VPS (hostdata.id 4C/16GB Ubuntu 24.04).
- Configure tunnel to expose only the Discord webhook endpoint (e.g., `https://guinevere.example.com/webhook/discord`).
- Store Cloudflare tunnel credentials via SOPS + age encryption per ADR-015.
- Configure Cloudflare Access or application-layer authentication to validate webhook signatures.
- Monitor tunnel health via Prometheus + Grafana (ADR-017).
- Test tunnel failover behavior: if cloudflared stops, webhook delivery fails but no other services are affected.
- Document the exact systemd unit file and Cloudflare tunnel configuration in deployment runbook.
- Implementation must update the relevant v2.0 source documents or future superseding specs if this ADR changes state.
- Accepted ADRs must not be edited in-place for material decision changes; create a superseding ADR instead.
- Proposed ADRs require Faiz approval before they become binding runtime policy.
- Any sub-agent research, implementation summary, audit, or verification used for this ADR must be written to markdown evidence, not returned only inline.

## Review Record

- **Date:** 2026-05-30
- **Reviewer:** Senior Architect Reviewer / Guinevere
- **Decision:** Accepted
- **Evidence:** Reviewed against Guinevere_TechnicalArchitecture_v2.0.md, Guinevere_APIIntegration_v2.0.md, ADR-019, and 210-question feasibility assessment responses confirming operator requirement for minimum one public endpoint.
- **Notes:**
  - **Scope:** Only Discord webhook endpoint exposed. No other services (API, admin, monitoring) are publicly accessible.
  - **Cost:** Free tier sufficient. No additional monthly cost.
  - **Operator confirmation:** Faiz explicitly confirmed "minimum 1 public endpoint HARUS ada" during feasibility Q&A.
  - **Security:** Cloudflare Tunnel provides better security than direct IP exposure. No VPS IP disclosure. Automatic TLS.

## Links

- [`../Guinevere_TechnicalArchitecture_v2.0.md`](../Guinevere_TechnicalArchitecture_v2.0.md)
- [`./ADR-019-access-control-vpn-mesh-strategy.md`](./ADR-019-access-control-vpn-mesh-strategy.md)
- [`../Guinevere_APIIntegration_v2.0.md`](../Guinevere_APIIntegration_v2.0.md)
- [`../Guinevere_ADR_Index_v1.0.md`](../Guinevere_ADR_Index_v1.0.md)
