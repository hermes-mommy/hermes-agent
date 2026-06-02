---
adr: 028
title: "LLM Router Outage — 9Router Combo Routing with Graceful Degradation"
status: "Superseded"
date: "2026-05-30"
superseded_date: "2026-06-01"
deciders:
  - "Faiz (Owner, solo developer Indonesia)"
  - "Guinevere (Executor / autonomous system steward)"
tags:
  - llm
  - fallback
  - graceful-degradation
  - resilience
  - 9router
  - deepseek
  - cockpit
  - opencode-go
risk_level: "MEDIUM"
supersedes: "N/A"
superseded_by: "migration-9router decisions (2026-06-01)"
related_documents:
  - adr/ADR-004-primary-llm-model-selection.md
  - adr/ADR-005-llm-router-failover-strategy.md
  - adr/ADR-006-sub-agent-llm-model-strategy.md
  - docs/setup-evidence/P1/migration-9router/evidence.md
  - audit-reports/P1/migration-9router/guinevere-combo-routing-auditor-report.md
---

# ADR-028: LLM Router Outage — 9Router Combo Routing with Graceful Degradation

## Status

Superseded.

**Superseded by:** `migration-9router` decisions from 2026-06-01.

**Supersession decision:** Ollama local fallback is **not implemented** for Guinevere P1.

## Date

2026-05-30; superseded on 2026-06-01.

## Deciders

Faiz (Owner, solo developer Indonesia); Guinevere (Executor / autonomous system steward)

## Tags

llm, fallback, graceful-degradation, resilience, 9router, deepseek, cockpit, opencode-go

## Risk Level

MEDIUM

## Supersedes

N/A

## Superseded By

`migration-9router` decisions documented in:

- `docs/setup-evidence/P1/migration-9router/evidence.md`
- `audit-reports/P1/migration-9router/guinevere-combo-routing-auditor-report.md`

## Related Documents

| Document | Relationship |
|---|---|
| [`ADR-004`](ADR-004-primary-llm-model-selection.md) | Primary LLM model selection (GPT-5.5 via 9Router) |
| [`ADR-005`](ADR-005-llm-router-failover-strategy.md) | LLM router and failover strategy, now interpreted through 9Router combo routing plus graceful degradation |
| [`ADR-006`](ADR-006-sub-agent-llm-model-strategy.md) | Sub-agent LLM model strategy (DeepSeek V4 Flash) |
| `docs/setup-evidence/P1/migration-9router/evidence.md` | Binding implementation evidence for 9Router migration and Guinevere combo routing |
| `audit-reports/P1/migration-9router/guinevere-combo-routing-auditor-report.md` | Auditor PASS for Guinevere combo routing |
| `Guinevere_TechnicalArchitecture_v2.0.md` | Runtime architecture, systemd services, infrastructure constraints |
| `Guinevere_AgentLoopSpec_v2.0.md` | Canonical 7-phase SDLC loop behavior during degraded modes |
| `Guinevere_Cost_FinOps_Model_v1.0.md` | Budget constraints and low-cost routing rationale |

## Context

ADR-028 originally accepted a cloud-plus-local fallback design in which Guinevere would use 9Router first, then a secondary cloud path, then Ollama local inference, then graceful degradation. That design assumed Ollama was necessary as a low-cost third-level fallback if cloud routing became unavailable.

The 2026-06-01 9Router migration changed the runtime reality. Guinevere now has a dedicated 9Router combo named `guinevere` with working real-provider routing and verified model responses. The combo avoids the need for an Ollama local model in P1 because DeepSeek V4 Flash is available as a low-cost primary path through `opencode-go`, while GPT-5.5 remains available as a secondary path through `cockpit` over Tailscale.

Final runtime instruction after migration:

```text
OPENAI_BASE_URL=http://100.94.104.22:20128/v1
model=guinevere
```

Final `guinevere` combo order:

```text
Primary:   opencode-go/deepseek-v4-flash
Secondary: openai-compatible-chat-d2069ce0-65f4-4191-b91f-9065118c7a0e/gpt-5.5
Fallback:  Graceful degradation
```

## Decision Drivers

- The 9Router migration produced a more robust practical routing layer than the original Ollama fallback plan.
- DeepSeek V4 Flash is already available as a low-cost primary model through `opencode-go`.
- GPT-5.5 is available as a secondary route through the `cockpit` provider over Tailscale.
- Ollama would add operational complexity: model downloads, service lifecycle, RAM pressure, cold starts, and additional maintenance.
- Local Ollama inference is no longer required to satisfy the P1 resilience objective.
- Graceful degradation remains the correct final fallback when remote model routing is unavailable.
- Avoiding Ollama preserves VPS RAM and reduces risk to PostgreSQL, Redis, 9Router, and Guinevere core services.

## Decision Outcome

Chosen option: **skip Ollama local fallback** and rely on the migrated 9Router combo routing plus graceful degradation.

### Active Routing Chain

```text
1. DeepSeek V4 Flash via opencode-go
   → low-cost primary route for Guinevere combo calls

2. GPT-5.5 via cockpit over Tailscale
   → secondary route when available; depends on laptop cockpit service being online

3. Graceful degradation
   → no LLM, basic health/status/queued-task behavior only
```

### Explicit Non-Decision

Ollama local fallback is not installed, not configured, and not tested for P1. Steps P1-012, P1-013, and P1-014 are intentionally marked **SKIPPED** per Faiz directive on 2026-06-01.

### Impact on P1 Steps

| Step | Previous meaning | New status | Reason |
|---|---|---|---|
| P1-012 | Ollama installation | SKIPPED | Ollama not needed after 9Router migration |
| P1-013 | Ollama model pull | SKIPPED | No local model required |
| P1-014 | Ollama fallback test | SKIPPED | Graceful degradation replaces Ollama fallback |

## Consequences

### Positive

- Simpler runtime: no Ollama service, model storage, or local inference lifecycle.
- Lower VPS memory pressure: no 4GB Ollama cap reservation during outage scenarios.
- Lower operational maintenance: no local model updates, pulls, or corruption recovery.
- Real low-cost primary path exists now: DeepSeek V4 Flash via `opencode-go`.
- GPT-5.5 remains available as a secondary high-capability path through `cockpit`.
- Graceful degradation remains deterministic and easier to audit than low-quality local inference.

### Negative

- If both remote routes are unavailable, Guinevere has no local LLM inference fallback.
- The GPT-5.5 secondary path depends on laptop cockpit availability over Tailscale.
- Full offline operation is intentionally deferred rather than solved with local inference.

### Risks

- Extended remote-provider outage moves directly to graceful degradation.
- If `opencode-go` provider balance/quota fails and laptop cockpit is offline, Guinevere degrades without a local LLM.
- Future requirements for full offline operation would require a new ADR or a new superseding decision.

## Implementation Notes

- Do not install Ollama for P1 unless Faiz issues a new directive.
- Do not create `guinevere-ollama.service` under the current P1 plan.
- Do not pull `llama3.1:8b` or any other local fallback model for P1.
- Update Hermes config so the Ollama fallback section is removed or explicitly disabled.
- Track P1-012, P1-013, and P1-014 as skipped-but-counted steps because the project decision intentionally resolves them.
- Keep graceful degradation as the terminal fallback state.
- Keep evidence in `docs/setup-evidence/P1/adr-028-skip-ollama.md`.

## Revision History

| Date | Revision | Author | Detail |
|---|---|---|---|
| 2026-05-30 | v1.0 | Guinevere | Initial: Ollama local LLM fallback |
| 2026-05-30 | v2.0 | Faiz (operator directive) | Replaced Ollama fallback with graceful degradation mode. Added OpenRouter as secondary router. |
| 2026-05-30 | v3.0 | Faiz (operator directive) | Restored Ollama as third-level fallback. Full chain: 9Router → OpenRouter → Ollama → Graceful Degradation. Status upgraded to Accepted. |
| 2026-06-01 | v4.0 | Faiz (operator directive) | Superseded Ollama fallback. 9Router migration established `guinevere` combo routing: DeepSeek V4 Flash via `opencode-go` primary, GPT-5.5 via `cockpit` secondary, graceful degradation fallback. P1-012/P1-013/P1-014 skipped. |

## Links

- [`ADR-004`](ADR-004-primary-llm-model-selection.md)
- [`ADR-005`](ADR-005-llm-router-failover-strategy.md)
- [`ADR-006`](ADR-006-sub-agent-llm-model-strategy.md)
- [`../docs/setup-evidence/P1/migration-9router/evidence.md`](../docs/setup-evidence/P1/migration-9router/evidence.md)
- [`../audit-reports/P1/migration-9router/guinevere-combo-routing-auditor-report.md`](../audit-reports/P1/migration-9router/guinevere-combo-routing-auditor-report.md)
