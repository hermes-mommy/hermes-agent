# Evidence: Obscura CDP Browser Server Installation

**Date:** 2026-06-09
**Task:** Install Obscura CDP browser server for MCP tool `obscura_cdp` browser automation
**Operator:** Faiz (infrastructure direction)
**Agent:** Guinevere (installation, service configuration, verification)

---

## 1. Prior State

- **Obscura not installed** — binary absent from system
- **P6 smoke test result:** `obscura_cdp` tool returned **SKIP** (no CDP server available)
- **Need:** MCP tool `obscura_cdp` requires a CDP (Chrome DevTools Protocol) server endpoint for browser automation tasks

---

## 2. What Was Done

### 2.1 Binary Download & Installation

- Downloaded Obscura v0.1.7 from:
  `https://github.com/h4ckf0r0day/obscura/releases/latest/download/obscura-x86_64-linux.tar.gz`
- Extracted to `/home/guinevere/data/obscura/`
- Binaries installed:
  - `/home/guinevere/data/obscura/obscura` (main process)
  - `/home/guinevere/data/obscura/obscura-worker` (worker process)

### 2.2 Systemd Service Configuration

Service file: `/etc/systemd/system/guinevere-obscura.service`

The service file already existed but had an incorrect `ExecStart` path pointing to `/usr/local/bin/obscura` (binary not present there). Updated to:

```
ExecStart=/home/guinevere/data/obscura/obscura --port 9222 --stealth --workers 2
```

Service configuration:

| Setting | Value |
|---------|-------|
| ExecStart | `/home/guinevere/data/obscura/obscura --port 9222 --stealth --workers 2` |
| MemoryHigh | 256M |
| MemoryMax | 512M |
| CPUQuota | 100% |
| ProtectSystem | full |
| Slice | guinevere.slice |

### 2.3 Service Enable & Start

```bash
systemctl daemon-reload
systemctl enable --now guinevere-obscura
```

---

## 3. Running Processes

| Process | Port | Role |
|---------|------|------|
| obscura (main) | 9222 | CDP server, accepts WebSocket connections |
| obscura-worker | 9223 | Browser worker instance |
| obscura-worker | 9224 | Browser worker instance |

Total: **3 processes** (1 main + 2 workers)

---

## 4. CDP Endpoint

| Field | Value |
|-------|-------|
| WebSocket URL | `ws://127.0.0.1:9222` |
| Protocol | Chrome DevTools Protocol (CDP) |

---

## 5. Stealth Mode Features

Obscura runs with `--stealth` flag, enabling:

- **TLS fingerprint spoofing** — randomized TLS client hello to avoid fingerprinting
- **Tracker blocklist** — 3,520 domains blocked by default
- **Per-session fingerprint randomization** — unique browser fingerprint per session

---

## 6. Integration with Playwright

| Field | Value |
|-------|-------|
| Playwright version | 1.60.0 (in `.venv`) |
| Connection method | `async_playwright` → `chromium.connect_over_cdp()` |
| CDP URL passed | `ws://127.0.0.1:9222` |

---

## 7. Limitations (NOT Supported)

The following Playwright features are **not supported** by Obscura:

- `page.screenshot()` — screenshot capture unavailable
- `page.pdf()` — PDF generation unavailable
- Service Workers — not supported
- `file://` URLs — local file access not supported

---

## 8. Validation

- Service status: `active (running)` ✅
- CDP endpoint reachable on `ws://127.0.0.1:9222` ✅
- All 3 processes running (main + 2 workers) ✅
- `systemctl is-enabled guinevere-obscura` → `enabled` ✅

---

## 9. Rollback

```bash
systemctl disable --now guinevere-obscura
rm /home/guinevere/data/obscura/obscura /home/guinevere/data/obscura/obscura-worker
# Restore old ExecStart if needed
```

---

## 10. Caveats

- Obscura is a niche CDP browser tool from `h4ckf0r0day` — limited community support
- Stealth features may break if upstream changes fingerprinting logic
- No screenshot/PDF support limits certain automation use cases
- Workers consume separate memory; total memory footprint ≈ 512M under load
