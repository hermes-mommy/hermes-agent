# Guinevere — Project Decisions Log

> Consolidated record of significant project decisions, including architecture choices, tooling adoption, and strategic pivots. Each entry links to the relevant ADR for full context.

## Format

| # | Date | Decision | Category | ADR | Rationale | Approved By |
|---|------|----------|----------|-----|-----------|-------------|

## Decisions

| # | Date | Decision | Category | ADR | Rationale | Approved By |
|---|------|----------|----------|-----|-----------|-------------|
| 001 | 2026-06-02 | Adopt Obscura CDP as browser automation runtime | Tooling | [ADR-033](../../adr/ADR-033-browser-automation-obscura.md) | Replace Playwright + headless Chromium with Obscura CDP server (Rust, Apache-2.0, 14K stars). Stealth anti-detection built-in, 5x lighter, systemd-managed. Playwright retained as CDP client via `connect_over_cdp`. Supersedes ADR-020 at implementation level; strategic decision (obscura primary + Playwright fallback) unchanged. | Faiz |
| 002 | 2026-06-03 | Revise ADR-022 WhatsApp implementation from Baileys to Neonize | Architecture | [ADR-022](../../adr/ADR-022-communication-channel-strategy.md) | Replace Baileys (Node.js, WhatsApp Web MD) with Neonize (pure Python, wraps whatsmeow via CGo). Eliminates Node.js subprocess bridge, single Python process, native asyncio, pip-installable. Session storage corrected from Redis to PostgreSQL. Ban risk <2%/year reactive-only. Rollback: Baileys/Evolution API remains viable fallback. | Faiz |
| 003 | 2026-06-04 | Adopt Hermes NousResearch hybrid migration architecture | Architecture | [ADR-035](../../adr/ADR-035-hermes-migration.md) | Migrate Discord gateway to Hermes native (31.2% net code reduction, 44.2% of affected code). Hybrid memory (PostgreSQL primary + Hermes compression read-only). Safety ported to 7 lifecycle hooks + GuinevereSafetyPlugin. MCP hybrid (5 native + 7 custom). 9Router retained. 8-phase migration over 35-50 days. Phase 1 safety gate mandatory. Rollback: `hermes gateway stop` + `git checkout`. | Faiz (Accepted) |
| 004 | 2026-06-05 | ADR-030 Redis DB Assignment Reconciliation | Infrastructure | [ADR-030](../../adr/ADR-030-redis-db-assignments.md) (Revised) | ADR-030 Redis DB assignments reconciled with runtime code. Runtime state is authoritative for infrastructure assignments; documentation updated to match actual usage. DB0-BD5 mappings completely revised. Triggered by StepPrompts audit (Workstream 2 of dual-workstream execution). | Faiz |

---

*Last updated: 2026-06-05*
