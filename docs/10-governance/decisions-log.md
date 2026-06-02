# Guinevere — Project Decisions Log

> Consolidated record of significant project decisions, including architecture choices, tooling adoption, and strategic pivots. Each entry links to the relevant ADR for full context.

## Format

| # | Date | Decision | Category | ADR | Rationale | Approved By |
|---|------|----------|----------|-----|-----------|-------------|

## Decisions

| # | Date | Decision | Category | ADR | Rationale | Approved By |
|---|------|----------|----------|-----|-----------|-------------|
| 001 | 2026-06-02 | Adopt Obscura CDP as browser automation runtime | Tooling | [ADR-033](../../adr/ADR-033-browser-automation-obscura.md) | Replace Playwright + headless Chromium with Obscura CDP server (Rust, Apache-2.0, 14K stars). Stealth anti-detection built-in, 5x lighter, systemd-managed. Playwright retained as CDP client via `connect_over_cdp`. Supersedes ADR-020 at implementation level; strategic decision (obscura primary + Playwright fallback) unchanged. | Faiz |

---

*Last updated: 2026-06-02*
