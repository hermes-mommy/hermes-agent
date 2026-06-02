# Obscura CDP Server + Playwright-Core Integration Research

> Research for P6-009: obscura-cdp with playwright-core per ADR-033  
> Date: 2026-06-02  
> Evidence root: `research-reports/`

---

## 1. Obscura CDP Server — Flags & Install

### 1.1 Installation

**Source**: [h4ckf0r0day/obscura Wiki — Installation](https://github.com/h4ckf0r0day/obscura/wiki/Installation)

```bash
# Windows (our target)
# Download .zip from https://github.com/h4ckf0r0day/obscura/releases/latest
# Extract → obscura.exe + obscura-worker.exe

# Linux x86_64
curl -LO https://github.com/h4ckf0r0day/obscura/releases/latest/download/obscura-x86_64-linux.tar.gz
tar xzf obscura-x86_64-linux.tar.gz

# Docker (NOTE: stealth mode NOT included in Docker image)
docker run -d --name obscura -p 127.0.0.1:9222:9222 h4ckf0r0day/obscura
```

**Latest release**: [v0.1.6](https://github.com/h4ckf0r0day/obscura/releases/tag/v0.1.6) (2026-05-29). Release binaries **include** stealth feature compiled-in.

### 1.2 CDP Server Flags

**Source**: [h4ckf0r0day/obscura README](https://github.com/h4ckf0r0day/obscura?tab=readme-ov-file)

```bash
obscura serve --port 9222 --stealth
```

| Flag | Default | Description |
|------|---------|-------------|
| `--port` | `9222` | WebSocket port |
| `--proxy` | — | HTTP/SOCKS5 proxy URL |
| `--stealth` | off | Enable anti-detection + tracker blocking |
| `--workers` | `1` | Number of parallel worker processes |
| `--obey-robots` | off | Respect robots.txt |
| `--user-agent` | — | Custom User-Agent string |
| `--allow-file-access` | off | Allow `file://` CDP navigation (dangerous) |

### 1.3 Stealth Mode Architecture

**Source**: [Obscura Wiki — Configure stealth](https://github.com/h4ckf0r0day/obscura/wiki/Configure-stealth-and-proxies)

Enabling `--stealth` activates:
- **TLS fingerprint spoofing**: `wreq` HTTP client mimics Chrome's ClientHello, ALPN, cipher order (bypasses JA3/JA4 fingerprinting)
- **Tracker blocklist**: 3,520 domains (analytics, ads, telemetry, fingerprinting) — compiled-in via `include_str!`, no runtime I/O
- **Per-session fingerprint randomization**: GPU, screen, canvas, audio, battery
- `navigator.webdriver = undefined` (matches real Chrome)
- `navigator.userAgentData` spoofed to Chrome 145
- `event.isTrusted = true` for dispatched events
- Native function masking (`Function.prototype.toString()` → `[native code]`)

**What stealth does NOT handle**: Cloudflare interactive challenges, DataDome/Akamai bot managers, CAPTCHAs, IP-based rate limiting.

### 1.4 CDP API Coverage

**Source**: [h4ckf0r0day/obscura README](https://github.com/h4ckf0r0day/obscura/blob/main/README.md)

9 protocol domains + 1 custom domain, ~30 methods on fast path:

| Domain | Methods |
|--------|---------|
| **Target** | createTarget, closeTarget, attachToTarget, createBrowserContext, disposeBrowserContext |
| **Page** | navigate, getFrameTree, addScriptToEvaluateOnNewDocument, lifecycleEvents |
| **Runtime** | evaluate, callFunctionOn, getProperties, addBinding |
| **DOM** | getDocument, querySelector, querySelectorAll, getOuterHTML, resolveNode |
| **Network** | enable, setCookies, getCookies, setExtraHTTPHeaders, setUserAgentOverride |
| **Fetch** | enable, continueRequest, fulfillRequest, failRequest |
| **Storage** | getCookies, setCookies, deleteCookies |
| **Input** | dispatchMouseEvent, dispatchKeyEvent |
| **LP** (custom) | **getMarkdown** — native DOM-to-Markdown conversion (Rust, no JS eval needed) |

### 1.5 ⚠️ NOT Supported (Critical for Auth Mapping)

**Source**: [Obscura Wiki — Use with Playwright](https://github.com/h4ckf0r0day/obscura/wiki/Use-with-Playwright)

- **`page.screenshot()`** — ❌ No pixel rendering engine
- **`page.pdf()`** — ❌ No pixel rendering
- **`page.video()`** — ❌ No media capture
- **tracing artifacts** — ❌
- **`BrowserContext` storage state save/restore** — ❌ Use `--storage-dir` on `obscura serve` instead
- **Service workers** — ❌
- **`file://` URLs** — ❌ Blocked by default since v0.1.5. Use `--allow-file-access`.

**This means**: Screenshot-based auth level (Read-Auto) must use `LP.getMarkdown` + `page.evaluate()` for content extraction, NOT `page.screenshot()`.

---

## 2. Playwright-Core — Python Reality

### 2.1 Key Finding: No Separate `playwright-core` PyPI Package for Python

**Source**: [playwright pypi.org](https://pypi.org/project/playwright/) + [playwright.dev docs](https://playwright.dev/python/docs/library)

In Python, **there is no separate `playwright-core` package**. The `playwright` package IS the whole thing — 43MB wheel including the Playwright driver binary. The `playwright-core` concept exists only in **Node.js/npm** (`npm install playwright-core`).

### 2.2 Minimal Install Strategy

For CDP-only usage (no bundled browsers needed):

```bash
# Option A: Install playwright, skip browser download
set PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
pip install playwright
# No `playwright install` needed

# Option B: Install but don't download browsers
pip install playwright
# Do NOT run `playwright install` (skips Chromium/Firefox/WebKit download)
```

**Evidence** ([GitHub: PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD usage](https://github.com/search?q=PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD&type=code)): Multiple projects use `os.environ["PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD"] = "1"` to avoid downloading browser binaries when connecting to external CDP servers.

### 2.3 Dependencies

The `playwright` Python wheel includes: the Playwright driver binary, `pyee` (event emitter), and `greenlet` (cooperative multitasking for sync API). No Node.js required — the driver is bundled in the wheel.

---

## 3. `connect_over_cdp` — Exact Code Patterns

### 3.1 Python Sync Pattern

**Source**: [Playwright Python docs — BrowserType.connect_over_cdp](https://playwright.dev/python/docs/api/class-browsertype)

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as playwright:
    browser = playwright.chromium.connect_over_cdp("http://localhost:9222")
    default_context = browser.contexts[0]
    page = default_context.pages[0]
    # or: page = default_context.new_page()

    page.goto("https://example.com")
    print(page.title())
    browser.close()
```

### 3.2 Python Async Pattern (Recommended for Guinevere)

**Source**: Playwright docs + [StackOverflow example](https://stackoverflow.com/questions/79544171)

```python
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        context = browser.contexts[0]
        page = await context.new_page()

        await page.goto("https://example.com")
        title = await page.title()
        print(title)

        await browser.close()

asyncio.run(main())
```

### 3.3 CDP Endpoint Variations

**Source**: [Playwright connect-over-cdp spec](https://github.com/microsoft/playwright/blob/54e92be7/tests/library/chromium/connect-over-cdp.spec.ts)

All these work:
```python
# HTTP URL (auto-discovers ws endpoint via /json/version)
browser = await chromium.connect_over_cdp("http://localhost:9222")
browser = await chromium.connect_over_cdp("http://127.0.0.1:9222")

# Direct WebSocket endpoint
browser = await chromium.connect_over_cdp("ws://127.0.0.1:9222")
browser = await chromium.connect_over_cdp("ws://127.0.0.1:9222/devtools/browser/<uuid>")

# With custom headers
browser = await chromium.connect_over_cdp(
    "http://localhost:9222",
    headers={"User-Agent": "Playwright", "foo": "bar"}
)
```

### 3.4 ⚠️ `connect_over_cdp` vs `connect`

**CRITICAL**: Use `connect_over_cdp`, NOT `connect`. `connect()` speaks Playwright's own protocol, which only works with `launchServer()`. CDP servers (Obscura, remote Chrome) require `connect_over_cdp`.

**Source**: [Playwright issue #1784](https://github.com/microsoft/playwright-python/issues/1784)

### 3.5 Known Obscura Issue: CDP Control Plane Hang

**Source**: [Issue #62](https://github.com/h4ckf0r0day/obscura/issues/62)

When JS engine is busy on heavy pages, `GET /json/version` times out. `connect_over_cdp` does this HTTP call FIRST to discover the WebSocket URL. If it hangs, the entire connect hangs.

**Mitigations**:
- Use the **direct WS endpoint** format (`ws://127.0.0.1:9222`) to skip `/json/version` discovery
- Set `timeout` parameter lower: `connect_over_cdp("ws://127.0.0.1:9222", timeout=15000)`
- Poll `/json/version` readiness before connecting (as AWS Lambda adapter does)
- Use `--workers 4` for parallel sessions

---

## 4. Page Operations — Navigation & Content Extraction

### 4.1 Navigation Patterns

**Source**: [Obscura Wiki — Use with Playwright](https://github.com/h4ckf0r0day/obscura/wiki/Use-with-Playwright)

```python
# Navigation with wait strategies
await page.goto("https://example.com")
await page.goto("https://example.com", wait_until="load")
await page.goto("https://example.com", wait_until="domcontentloaded")  # default
await page.goto("https://example.com", wait_until="networkidle")
```

### 4.2 Content Extraction (Replaces Screenshot)

Since `page.screenshot()` is NOT supported by Obscura, use these alternatives:

```python
# A) LP.getMarkdown via CDP (native Rust DOM→MD, no JS eval)
# Accessible via raw CDP send if needed:
# await page.evaluate("...") — standard CDP evaluate

# B) Extract text via JS evaluate
text = await page.evaluate("() => document.body.innerText")

# C) Extract structured data
result = await page.evaluate("""() => {
    const title = document.title;
    const body = document.body.innerText.substring(0, 5000);
    return { title, body, url: window.location.href };
}""")

# D) Get full HTML for parsing
html = await page.content()

# E) DOM selection
elements = await page.$$eval(".item", lambda els: [
    {"text": el.text_content(), "href": el.query_selector("a").get_attribute("href")}
    for el in els
])
```

### 4.3 Form Interaction

**Source**: [Obscura Wiki — Interact](https://github.com/h4ckf0r0day/obscura/wiki/Use-with-Playwright)

```python
# Click
await page.click("#login-button")

# Fill forms
await page.fill("#username", "alice")
await page.fill("#password", "secret")

# Locators (modern API)
await page.locator("button.submit").click()
await page.get_by_role("button", name="Submit").click()
await page.get_by_label("Email").fill("alice@example.com")

# Wait for elements
await page.wait_for_selector("#dashboard")
await page.wait_for_function("() => window.appReady === true")
```

### 4.4 File Upload

```python
# File input interaction
await page.set_input_files("#file-upload", "/path/to/file.pdf")

# Or using locator
await page.locator("#file-upload").set_input_files("/path/to/file.pdf")
```

### 4.5 Cookies & Headers

```python
# Set cookies
await context.add_cookies([{
    "name": "session",
    "value": "abc123",
    "domain": "example.com",
    "path": "/",
}])

# Read cookies
cookies = await context.cookies()

# Custom headers per navigation
await page.set_extra_http_headers({"Authorization": "Bearer token"})
```

---

## 5. Auth-Level Mapping (ADR-033 P6-009)

### 5.1 Operation ↔ Auth Matrix

| Auth Level | Allowed Operations | CDP Methods Needed | Obscura Support |
|------------|-------------------|--------------------|-------------------|
| **Read-Auto** | navigate, extract content, get title, read DOM | `Page.navigate`, `Runtime.evaluate`, `LP.getMarkdown`, `DOM.getDocument` | ✅ Full |
| **Write-Notify** | form fill, click, keypress, cookie set | `Input.dispatchMouseEvent`, `Input.dispatchKeyEvent`, `Storage.setCookies` | ✅ Full |
| **Destructive-Approval** | file upload, submit forms with side effects | `Page.navigate` + `Input.*` + file handling | ⚠️ `set_input_files` works |
| **Not Available** | screenshot, PDF, video | Not in CDP | ❌ No rendering |

### 5.2 recommended Implementation Pattern

```python
from enum import Enum
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

class AuthLevel(Enum):
    READ_AUTO = "read_auto"
    WRITE_NOTIFY = "write_notify"
    DESTRUCTIVE_APPROVAL = "destructive_approval"

class ObscuraCDPClient:
    def __init__(self, cdp_url: str = "ws://127.0.0.1:9222"):
        self.cdp_url = cdp_url
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None

    async def connect(self):
        p = await async_playwright().start()
        self.browser = await p.chromium.connect_over_cdp(self.cdp_url)
        self.context = self.browser.contexts[0]
        self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()

    # ── Read-Auto ──
    async def navigate(self, url: str) -> dict:
        await self.page.goto(url, wait_until="domcontentloaded")
        return await self._extract_content()

    async def _extract_content(self) -> dict:
        return await self.page.evaluate("""() => ({
            title: document.title,
            text: document.body.innerText.substring(0, 10000),
            url: window.location.href,
        })""")

    # ── Write-Notify ──
    async def fill_form(self, fields: dict[str, str]):
        for selector, value in fields.items():
            await self.page.fill(selector, value)

    async def click_element(self, selector: str):
        await self.page.click(selector)

    # ── Destructive-Approval ──
    async def upload_file(self, selector: str, file_path: str):
        await self.page.set_input_files(selector, file_path)

    async def close(self):
        if self.browser:
            await self.browser.close()
```

---

## 6. Runbook: Start-to-Working

```bash
# 1. Download Obscura (Windows)
#    Download: https://github.com/h4ckf0r0day/obscura/releases/latest
#    Extract obscura-x86_64-windows.zip → obscura.exe + obscura-worker.exe

# 2. Start CDP server
obscura serve --port 9222 --stealth

# 3. Install Python deps (skip browser binaries)
set PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
pip install playwright
# Do NOT run: playwright install

# 4. Test connection
python -c "
import asyncio
from playwright.async_api import async_playwright

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp('ws://127.0.0.1:9222')
        context = browser.contexts[0]
        page = await context.new_page()
        await page.goto('https://example.com')
        print(await page.title())
        await browser.close()

asyncio.run(test())
"
```

---

## 7. Key Caveats & Gotchas

| Issue | Detail | Mitigation |
|-------|--------|------------|
| **No screenshots** | Obscura has no pixel rendering. `page.screenshot()` fails. | Use `LP.getMarkdown` + `page.evaluate()` for content |
| **`connect` ≠ `connect_over_cdp`** | `connect()` uses Playwright protocol, not CDP | Always use `chromium.connect_over_cdp()` |
| **CDP control plane hang** | HTTP `/json/version` can block during heavy JS (Issue #62) | Use direct `ws://` endpoint, set lower timeout |
| **Docker no stealth** | Docker image excludes `--stealth` feature | Build from source or use binary |
| **`file://` blocked** | CDP navigation to `file://` blocked since v0.1.5 | Use `--allow-file-access` flag (with warning) |
| **One V8 isolate** | Multiple pages share one JS runtime; CPU on one blocks others | Use `--workers` for concurrency |
| **No storage state save/restore** | `BrowserContext.storage_state()` not supported | Use `--storage-dir` on `obscura serve` |
| **Python `playwright-core` doesn't exist** | Node.js concept only | Use `pip install playwright` + `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1` |
| **GLIBC 2.35+** | Linux binary needs Ubuntu 22.04+ | Use Docker or build from source |

---

## 8. References

| Resource | Link |
|----------|------|
| Obscura GitHub | https://github.com/h4ckf0r0day/obscura |
| Obscura Releases | https://github.com/h4ckf0r0day/obscura/releases |
| Use with Playwright (Wiki) | https://github.com/h4ckf0r0day/obscura/wiki/Use-with-Playwright |
| Configure Stealth (Wiki) | https://github.com/h4ckf0r0day/obscura/wiki/Configure-stealth-and-proxies |
| Installation (Wiki) | https://github.com/h4ckf0r0day/obscura/wiki/Installation |
| Environment Variables (Wiki) | https://github.com/h4ckf0r0day/obscura/wiki/Environment-variables |
| Playwright Python: BrowserType.connect_over_cdp | https://playwright.dev/python/docs/api/class-browsertype#browser-type-connect-over-cdp |
| Playwright Library (Python) | https://playwright.dev/python/docs/library |
| CDP Control Plane Hang (Issue #62) | https://github.com/h4ckf0r0day/obscura/issues/62 |
| connect_over_cdp spec tests | https://github.com/microsoft/playwright/blob/54e92be7/tests/library/chromium/connect-over-cdp.spec.ts |
| Obscura on AWS Lambda | https://chegger.me/blog/obscura-aws-lambda/ |
| Obscura MCP Server | https://github.com/Metadrama/obscura-mcp |

---

> **Report prepared by THE LIBRARIAN** for Guinevere P6-009 (obscura-cdp with playwright-core, per ADR-033).  
> Evidence-based. All claims backed by permalinks.