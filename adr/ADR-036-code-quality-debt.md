---
adr: 036
title: "Code Quality Debt Tracking and Cleanup"
status: "Proposed"
date: "2026-06-07"
deciders:
  - "Faiz (Owner, solo developer Indonesia)"
  - "Guinevere (Executor / autonomous system steward)"
tags:
  - code-quality
  - tech-debt
  - maintenance
  - type-safety
risk_level: "LOW"
supersedes: null
related_documents:
  - docs/setup-evidence/phase6-audit/03-code-quality.md
  - docs/setup-evidence/phase6-audit/VERIFICATION-SUMMARY.md
---

# ADR-036: Code Quality Debt Tracking and Cleanup

## Status

Proposed

## Date

2026-06-07

## Deciders

Faiz (Owner, solo developer Indonesia); Guinevere (Executor / autonomous system steward)

## Tags

code-quality, tech-debt, maintenance, type-safety

## Risk Level

LOW

## Supersedes

null

## Context

Phase 6 System Audit (ADR-035 compliance) identified 11 active `# type: ignore` directives scattered across `src/` modules. These are **pre-ADR-035** code quality debt — none were introduced by the Hermes migration.

**Distribution (11 active, 0 in `src/hermes/`):**

| File | Count | Module |
|---|---|---|
| `src/observability/sentry_integration.py` | 5 | Observability |
| `src/mcp/auth.py` | 2 | MCP |
| `src/surveillance/timescale.py` | 1 | Surveillance |
| `src/mcp/tools/postgres_tool.py` | 1 | MCP |
| `src/discord/_entrypoint.py` | 1 | Discord |
| `src/core/main.py` | 1 | Core |

**Additional debt identified in Phase 6 audit:**
- 20 broad `except Exception` in `hermes-config/hooks/` safety plugin (Hermes SDK error types not importable)
- 71 stale StepPrompts markers (cleaned separately in Phase 6 audit follow-up)

## Decision

Track this code quality debt in ADR-036 and address it in a **future maintenance pass** (not blocking current work). The cleanup will be performed module-by-module as each module undergoes its next substantive change.

**Cleanup approach:**
1. `src/observability/sentry_integration.py` (5 `# type: ignore`) — Replace with typed Sentry SDK imports or explicit cast patterns when Sentry SDK is next updated.
2. `src/mcp/auth.py` (2 `# type: ignore`) — Type the auth matrix decorators properly using generic type parameters.
3. `src/surveillance/timescale.py` (1 `# type: ignore`) — Type the TimescaleDB async connection parameters.
4. `src/mcp/tools/postgres_tool.py` (1 `# type: ignore`) — Type the asyncpg connection pool initialization.
5. `src/discord/_entrypoint.py` (1 `# type: ignore`) — Type the Discord bot entrypoint after Hermes cutover stabilization.
6. `src/core/main.py` (1 `# type: ignore`) — Type the application bootstrap sequence.

**Broad `except Exception` in hermes-config/hooks/:** These are constrained by the Hermes SDK's error type surface. When Hermes SDK exposes typed error classes, replace with specific exception handlers.

## Consequences

### Positive
- Code quality debt is tracked, not forgotten
- Cleanup is scoped per-module, reducing blast radius
- No risk of breaking working code during a large-scale type cleanup
- Phase 6 audit findings are formally documented

### Negative
- 11 `# type: ignore` directives remain in the codebase until addressed
- mypy strict mode will continue to flag these locations
- Each module cleanup adds minor effort to its next change cycle

### Neutral
- This ADR does not block any current implementation work
- The `# type: ignore` directives are pre-existing and do not indicate new risk

## Affected Modules

| Module | `# type: ignore` Count | Priority | Estimated Effort |
|---|---|---|---|
| `src/observability/` | 5 | Medium | 30 min |
| `src/mcp/` | 3 | Medium | 45 min |
| `src/surveillance/` | 1 | Low | 15 min |
| `src/discord/` | 1 | Low | 15 min |
| `src/core/` | 1 | Low | 15 min |
| **Total** | **11** | — | **~2 hours** |

## Related ADRs

- **ADR-035** — Hermes Migration Architecture (Phase 6 audit source)
- **ADR-029** — Self-Modification Automated Testing (test infrastructure)

## Footer

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-07 | Guinevere | Initial proposal — Phase 6 audit finding |
