---
adr: 033
title: "Browser Automation — Obscura CDP over Headless Chrome + Playwright"
status: "Accepted"
date: "2026-06-02"
deciders:
  - "Faiz (Owner, solo developer Indonesia)"
  - "Guinevere (Executor / autonomous system steward)"
tags:
  - browser
  - obscura
  - cdp
  - playwright-core
  - automation
  - stealth
  - p6-009
risk_level: "MEDIUM"
supersedes: "Refines ADR-020 (implementation-level)"
related_documents:
  - adr/ADR-020-browser-automation-strategy.md
  - stepprompts/StepPrompts.md (P6-009)
  - docs/00-core/05-APIIntegration_v2.0.md
  - docs/60-persona/62-MCPConfigGuide_v1.0.md
---

# ADR-033: Browser Automation — Obscura CDP over Headless Chrome + Playwright

## Status

Accepted

## Date

2026-06-02

## Deciders

Faiz (Owner, solo developer Indonesia); Guinevere (Executor / autonomous system steward)

## Tags

browser, obscura, cdp, playwright-core, automation, stealth, p6-009

## Risk Level

MEDIUM

## Supersedes

Refines ADR-020 (implementation-level). ADR-020 remains the strategic decision (obscura primary + Playwright fallback). ADR-033 specifies the concrete implementation: Obscura CDP server + playwright-core client.

## Related Documents

| Document | Relationship |
|---|---|
| [`ADR-020-browser-automation-strategy.md`](ADR-020-browser-automation-strategy.md) | Strategic decision this ADR refines |
| [`../stepprompts/StepPrompts.md`](../stepprompts/StepPrompts.md) | P6-009 implementation step |
| [`../docs/00-core/05-APIIntegration_v2.0.md`](../docs/00-core/05-APIIntegration_v2.0.md) | API integration spec §8.2 |
| [`../docs/60-persona/62-MCPConfigGuide_v1.0.md`](../docs/60-persona/62-MCPConfigGuide_v1.0.md) | MCP tool configuration §3.8 |

## Context

P6-009 originally planned Playwright + headless Chromium for browser automation. Obscura ([github.com/h4ckf0r0day/obscura](https://github.com/h4ckf0r0day/obscura)) was evaluated as alternative:

- **License**: Apache-2.0
- **Community**: ~14K GitHub stars, 911 forks (as of June 2026)
- **Runtime**: Rust-based single binary (~70MB vs 300MB+ Chromium)
- **Memory**: ~30MB RAM vs 200MB+ headless Chrome
- **Protocol**: CDP-compatible (Playwright works unchanged via `connect_over_cdp`)
- **Stealth**: Built-in anti-detect/stealth mode
- **Performance**: ~85ms page load vs ~500ms Chrome
- **Dependencies**: No Node.js/Chrome dependencies required
- **Strategic value**: Critical for future X Auto-Poster (P13) where stealth is required

This decision refines ADR-020's strategic direction ("obscura primary + Playwright fallback") by specifying the concrete implementation architecture: Obscura as a CDP server with playwright-core as the client library.

## Decision Drivers

- VPS resource constraints (4C/16GB shared with Aizanta; Guinevere allocated 8GB).
- X Auto-Poster (P13) requires anti-detect capabilities for platform compliance.
- CDP compatibility preserves existing Playwright code investment.
- Single-binary deployment simplifies systemd service management.
- Cost neutrality ($0 for Obscura vs $0 for Chromium, but lower resource overhead).

## Considered Options

1. **Playwright + headless Chromium** (original P6-009 plan) — mature but heavy (300MB+ binary, 200MB+ RAM, no stealth).
2. **Obscura standalone** — lightweight but no Playwright API compatibility.
3. **Obscura CDP server + playwright-core client** — lightweight + Playwright API + stealth.
4. **Puppeteer + Chromium** — Node.js dependency, no stealth, heavier than Obscura.

## Decision

**Chosen option: Obscura CDP server + playwright-core client.**

Replace headless Chrome + full Playwright with Obscura CDP server + playwright-core.

### Runtime Architecture

**Server** (systemd service `guinevere-obscura.service`):

```bash
obscura serve --port 9222 --stealth --workers 2
```

**Client** (Python playwright-core):

```python
from playwright.async_api import async_playwright

async with async_playwright() as p:
    browser = await p.chromium.connect_over_cdp("ws://127.0.0.1:9222")
```

### Installation

```bash
curl -LO https://github.com/h4ckf0r0day/obscura/releases/latest/download/obscura-x86_64-linux.tar.gz
tar xzf obscura-x86_64-linux.tar.gz
sudo mv obscura /usr/local/bin/obscura
chmod +x /usr/local/bin/obscura
```

### Systemd Service

```ini
[Unit]
Description=Guinevere Obscura CDP Server
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/obscura serve --port 9222 --stealth --workers 2
User=guinevere
Slice=guinevere.slice
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### Playwright Fallback

Full Playwright with Chromium remains available as fallback per ADR-020 when Obscura cannot handle specific scenarios (complex multi-step forms, PDF generation, auth flows with credential input).

## Consequences

### Positive

- **6x memory reduction**: 30MB vs 200MB+ headless Chrome
- **Built-in anti-detect**: Critical for X Auto-Poster (P13) stealth requirements
- **Single binary deployment**: No Chrome/Chromium dependency, no Node.js
- **Faster startup and page load**: ~85ms vs ~500ms
- **CDP-compatible**: Existing playwright-core code works unchanged
- **$0 cost**: Apache-2.0 license, no API fees
- **VPS-friendly**: Lower resource footprint on shared 4C/16GB VPS

### Negative / Risks

- **Pre-1.0**: v0.1.6 (April 2026) — early stage, API surface may change between releases
- **Young project**: ~50 days old at time of adoption; active CDP parity fixes in changelog
- **No production track record**: Untested in production environments at Guinevere scale
- **Partial CDP coverage**: 9 of 40+ Chrome DevTools Protocol domains implemented; edge cases may break
- **Self-reported benchmarks**: 30MB RAM, 85ms page load — no independent verification linked
- **Binary availability**: Dependent on GitHub releases; no apt package (AUR available: `obscura-browser`)
- **Fallback complexity**: Two browser paths require clear routing logic
- **Contributor concentration**: Top 3 contributors account for ~78 visible commits (bus factor concern)

### Mitigations

- Playwright + Chromium fallback documented and tested (ADR-020).
- Rollback plan documented below.
- Monitor Obscura releases for breaking changes.
- Test CDP coverage against Guinevere's specific use cases before production.

## Rollback Plan

If Obscura proves unstable or CDP coverage is insufficient:

```bash
# Stop and disable Obscura
sudo systemctl stop guinevere-obscura
sudo systemctl disable guinevere-obscura

# Install Chromium + Playwright fallback
apt install -y chromium-browser
pip install playwright
playwright install chromium

# Update P6-009 service to use Chromium directly
# Update MCP config to point to Playwright + Chromium
# See ADR-020 for fallback architecture
```

Rollback time estimate: < 5 minutes.

## Implementation Notes

- P6-009 StepPrompts updated to reference Obscura CDP + playwright-core.
- Systemd service: `guinevere-obscura.service` (not `guinevere-playwright.service`).
- Port 9222 allocated for Obscura CDP (standard Chrome DevTools Protocol port).
- Workers set to 2 (balanced for shared VPS; Guinevere allocated 2 CPU cores).
- Stealth mode enabled by default for all browser automation.
- Fallback to Playwright + Chromium for: complex multi-step forms, PDF generation, API provider dashboard login with credential input.

## Links

- [Obscura GitHub](https://github.com/h4ckf0r0day/obscura)
- [ADR-020: Browser Automation Strategy](ADR-020-browser-automation-strategy.md)
- [P6-009 StepPrompts](../stepprompts/StepPrompts.md)
- [Expansion: X Auto-Poster (P13)](../docs/post-mvp/) (future)
