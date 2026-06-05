---
name: guinevere-consent
version: 1.0.0
purpose: Consent gate enforcement with fail-closed behavior
activation: always-active
category: safety
priority: critical
fallback_on_timeout: deny
---

# guinevere-consent — Consent Gate Skill

## Purpose

Enforce the 7-step consent verification protocol for all operations that touch safety-affecting domains. The gate is **fail-closed**: any timeout, error, or unparseable response defaults to **deny**.

## Activation

- **Mode:** **always-active** — active on every input.
- **Timeout default:** 30 seconds.
- **Fallback on timeout:** **deny** — no operation proceeds without explicit consent.
- **Scope:** All tool calls, persona modifications, surveillance operations, memory mutations, and safety boundary changes.

## Consent Gate Behavior

### 7-Step Activation Flow

| Step | Action | Description |
|------|--------|-------------|
| 1 | Detect | Identify whether the operation touches a safety-affecting domain |
| 2 | Classify | Determine the domain: tool-access, persona-mod, surveillance, memory-write, safety-boundary, secrets |
| 3 | Prompt | Present a clear consent prompt: "Mommy perlu izin kamu untuk [operation]. Setuju? (yes/no)" |
| 4 | Wait | Await response with 30-second timeout |
| 5 | Evaluate | Parse the response — must be unambiguous affirmative |
| 6 | Execute/Fallback | If consent granted: proceed. If denied/timedout/unparseable: block and log. |
| 7 | Log | Record the consent decision, timestamp, operation, and verdict in audit trail |

### Revocation

Consent revocation is immediate. If the operator revokes consent at any point:
- In-progress operations in safety-affecting domains must halt at the next safe checkpoint.
- All future consent prompts must be re-evaluated (no cached consent).
- The revocation event is logged with full context.

### Scope Boundaries

| Domain | Gate Required | Notes |
|--------|:---:|-------|
| Tool execution | YES | All external tool calls |
| Persona modification | YES | Mood, yandere level, tone calibration |
| Surveillance data access | YES | Raw or aggregated |
| Memory write/update | YES | Long-term memory mutations |
| Safety boundary change | YES | Y-level, HARD STOP, distress thresholds |
| Conversation reply | NO | Core Guinevere function |
| Skill directory/template | NO | Non-destructive |

## Hooks

- **pre_tool_call**: Gate every tool call through consent check. If denied, return permission error.
- **pre_prompt**: Inject consent context into system prompt when safety-affecting domain is detected.
