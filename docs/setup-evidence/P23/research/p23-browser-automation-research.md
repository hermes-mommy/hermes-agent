# P23 Research — Browser Automation (Playwright + Obscura CDP)

> Status: RESEARCH. Date: 2026-06-25. Author: Guinevere research subagent.
> Scope: P23 Embodied Operations / Personal OS Action Layer — browser executor (Playwright + Obscura CDP).
> Constraint: READ-ONLY research. No runtime code, deploy, or restart.

## 1. Objective

Produce the browser-automation research baseline for P23 "Embodied Operations / Personal OS Action Layer." P23 turns Guinevere from a conversational + API-integrated companion into an agent that can act in the world via the browser — navigating, clicking, filling forms, extracting text, and capturing artifacts on a user's behalf. This research:

1. Maps the **existing browser infrastructure** in the repo (Obscura CDP server, Playwright client, P13 abandoned browser path, systemd `guinevere-obscura.service`, port 9222) so P23 builds on what is already deployed rather than re-inventing.
2. Distills the **Playwright async API** surface P23 needs (connect_over_cdp vs launch, locators, auto-waiting, network-idle, tracing, HAR, video, screenshot, download) from official docs, with URLs + retrieval date.
3. Specifies the **isolation design** — dedicated context/profile per action, separate process, no shared cookies across surfaces — so a general browser action cannot leak into P13's consented stealth session or vice versa.
4. Defines **action primitives** (navigate, click, fill, extract_text, screenshot, scroll, wait, download) that are policy-gated, audited, and rollback-capable.
5. Defines the **artifact model** — full-page screenshot + DOM snapshot + HAR → artifact path with PII/secret redaction.
6. Enumerates **failure modes** and the self-debug path via HermesBrain.
7. Classifies **consent** (`p23:browser` scope) and the surveillance-class implications of screen capture.
8. Documents the **local fallback** (headless Chromium when Obscura CDP is down) and the **cost model** (browser $0; LLM cost for planner/extract).

This file is an input to the P23 enterprise planner and the 13-domain auditor matrix. It is not a runtime artifact.

## 2. Sources Consulted (local + Playwright official docs with URLs + retrieval date)

### 2.1 Local repo (ground truth)

| Source | Path | What it provides |
|---|---|---|
| ADR-020 Browser Automation Strategy | `adr/ADR-020-browser-automation-strategy.md` | Strategic decision: Obscura primary + Playwright fallback |
| ADR-033 Browser Automation — Obscura CDP over Headless Chrome + Playwright | `adr/ADR-033-browser-automation-obscura.md` | Concrete implementation: Obscura CDP server on port 9222 + playwright-core client; systemd unit; rollback plan |
| Existing MCP browser tool | `src/mcp/tools/obscura_cdp.py` | Live implementation: `obscura_navigate`, `obscura_get_markdown`, `obscura_fill_form`, `obscura_click`; tenacity retry; `connect_over_cdp` |
| P13 ADR revision | `docs/10-governance/P13-028-ADR-Revision.md` | P13 browser automation (Obscura CDP → Camoufox → Playwright) was **abandoned** and replaced by Official X API v2; documents why browser automation was fragile for posting |
| StepPrompts P13 section | `stepprompts/StepPrompts.md` (lines ~35700, 35883) | P13 used a **dedicated Obscura context on port 9223**, separate from MCP/general automation on port 9222 — the isolation pattern P23 must preserve |
| Service Catalog | `docs/40-operations/48-ServiceCatalog_v1.0.md` | `guinevere-obscura.service` entry (Obscura CDP server, stealth browser/CDP access) |
| Implementation Guide | `docs/IMPLEMENTATION_GUIDE.md` (line ~752) | Browser troubleshooting + connect_over_cdp pattern reference |
| PersonaSafetyPolicy §15.1 | `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` (line 467) | **Tool-risk gate** — runtime hook before filesystem/shell/git/**API** actions; prevents persona pressure from causing irreversible action |
| PromptInjection Model Safety F-10 | `docs/20-security/24-PromptInjection_ModelSafety_v1.0.md` (lines 1067, 1614) | F-10 "Irreversible action under persona pressure" = CRITICAL; mitigation = tool-risk gate + high-blast-radius check |
| P22 security/consent research | `docs/setup-evidence/P22/research/p22-security-consent-research.md` | 4-level auth matrix (L1-L4), per-scope consent, append-only hash-chained audit log, Fernet field-level encryption, SOPS/age secrets, rate-limit/circuit-breaker patterns |
| P21 voice plan | `docs/setup-evidence/P21/plan/p21-voice-interface-enterprise-plan.md` | Surveillance-class consent gating (8 gates), retention/redaction, HARD STOP first-class, fail-closed consent cache, feature-flag + kill-switch rollback — the exact patterns P23 reuses |
| P23 policy-gate research | `docs/setup-evidence/P23/research/p23-policy-gate-risk-classification-research.md` | Policy gate + risk classification baseline for P23 (sibling research) |
| Obscura adoption evidence | `docs/setup-evidence/decisions/obscura-adoption/auditor-gate.md` + `verification.md` | connect_over_cdp pattern verified, no Chromium install as primary |
| Camoufox navigate script | `scripts/navigate_camoufox.py` | Legacy Camoufox fallback artifact (browser.contexts[0]) |
| Cost model | `docs/70-finops/70-Cost_FinOps_Model_v1.1.md` (line ~249) | P13 browser automation cost notes (Obscura CDP $0, LLM caption cost) |

### 2.2 Playwright official docs (retrieved 2026-06-25)

All URLs retrieved on 2026-06-25 via Brave Search + Context7 (`/microsoft/playwright`).

| Topic | URL | Retrieval date |
|---|---|---|
| Playwright Python home / async API | https://playwright.dev/python | 2026-06-25 |
| BrowserType (connect_over_cdp, launch, launch_persistent_context) | https://playwright.dev/python/docs/api/class-browsertype | 2026-06-25 |
| Browser | https://playwright.dev/python/docs/api/class-browser | 2026-06-25 |
| BrowserContext (isolation, new_context) | https://playwright.dev/python/docs/api/class-browsercontext | 2026-06-25 |
| Page (goto, click, fill, screenshot, content, title, url, wait_for_load_state, wait_for_selector) | https://playwright.dev/python/docs/api/class-page | 2026-06-25 |
| Locator (auto-waiting, strict mode) | https://playwright.dev/python/docs/api/class-locator | 2026-06-25 |
| Locators guide | https://playwright.dev/python/docs/locators | 2026-06-25 |
| Auto-waiting / actionability | https://playwright.dev/python/docs/actionability | 2026-06-25 |
| Browser contexts / isolation guide | https://playwright.dev/python/docs/browser-contexts | 2026-06-25 |
| Tracing (start, stop, start_har, stop_har, screenshots, DOM snapshots) | https://playwright.dev/python/docs/api/class-tracing | 2026-06-25 |
| Release notes (artifacts_dir in connect_over_cdp, HAR+WebSocket, Ubuntu 26.04, screencast) | https://playwright.dev/python/docs/release-notes | 2026-06-25 |
| GitHub releases (connect_over_cdp is_local, no_defaults, artifacts_dir) | https://github.com/microsoft/playwright-python/releases | 2026-06-25 |
| PyPI package (async_api import pattern) | https://pypi.org/project/playwright/ | 2026-06-25 |
| Tracing + debugging (DeepWiki — video save_as for remote browsers) | https://deepwiki.com/microsoft/playwright-python/4.2-tracing-and-debugging | 2026-06-25 |
| Network-idle wait_for_load_state (scrapfly) | https://scrapfly.io/blog/answers/how-to-wait-for-page-to-load-in-playwright | 2026-06-25 |
| waitForSelector guide (Autify) | https://autify.com/blog/playwright-waitforselector | 2026-06-25 |
| Persistent context guide (BrowserStack) | https://www.browserstack.com/guide/playwright-persistent-context | 2026-06-25 |
| Contexts & isolation 2026 guide (qaskills) | https://qaskills.sh/blog/playwright-browser-contexts-isolation-guide | 2026-06-25 |

**Context7 query** (`/microsoft/playwright`, "Python async API connect_over_cdp launch browser page goto click fill screenshot locators auto-waiting network idle tracing HAR video artifacts download") confirmed: `context.tracing.start_har("trace.har")` / `context.tracing.stop_har()` are the first-class HAR APIs (v1.60+); `record_har_path` on `new_context` is the legacy alternative; HAR supports `content` policy `omit|embed|attach` and `mode` `full|minimal`; only one HAR per BrowserContext.

## 3. Findings

### 3.1 Existing-infra map

The repo already has a working, deployed browser stack. P23 extends it — it does not build a parallel one.

**Server side — `guinevere-obscura.service` (systemd):**
- Per ADR-033, the Obscura CDP server runs as a systemd unit: `obscura serve --port 9222 --stealth --workers 2`, `User=guinevere`, `Slice=guinevere.slice`, `Restart=on-failure`.
- Port 9222 is the standard Chrome DevTools Protocol port and is the one the MCP client connects to.
- Service Catalog (`48-ServiceCatalog_v1.0.md`) lists it as "Obscura CDP server for stealth browser / CDP access."
- Obscura is a Rust single binary (~70MB), ~30MB RAM, Apache-2.0, CDP-compatible (Playwright works unchanged via `connect_over_cdp`). Self-reported ~85ms page load. **Caveat from ADR-033:** pre-1.0 (v0.1.6 April 2026), ~9 of 40+ CDP domains implemented, self-reported benchmarks, young project, bus-factor concern. Playwright+Chromium fallback is documented and rollback is <5 minutes.

**Client side — `src/mcp/tools/obscura_cdp.py`:**
- Implements 4 MCP tools: `obscura_navigate` (READ_AUTO), `obscura_get_markdown` (READ_AUTO), `obscura_fill_form` (WRITE_NOTIFY), `obscura_click` (WRITE_NOTIFY).
- Connection: `async_playwright().start()` → `p.chromium.connect_over_cdp("ws://127.0.0.1:9222")`, single shared `Browser` + single shared `Page` held in a module-level `_BrowserState` singleton.
- Retry: tenacity, 3 attempts, 2s fixed wait, on `ConnectionRefusedError`/`OSError`; raises `ObscuraNotRunning` with the start command in the message.
- Timeouts: 30s page goto, 10s selector wait.
- **Critical gap for P23:** the current tool reuses one global `Page` across all calls — no per-action context isolation, no artifact capture, no HAR/tracing, no screenshot (the module docstring explicitly says "No `page.screenshot()` — Obscura has no pixel rendering"). P23 needs dedicated contexts, screenshots, DOM snapshots, and HAR — which means either (a) the Playwright-Chromium fallback for pixel/artifact capture, or (b) confirming Obscura's CDP coverage now includes Page.captureScreenshot + Tracing.

**P13 history — the cautionary tale:**
- P13 (X Auto Poster) originally used browser automation via a **dedicated Obscura context on port 9223**, separate from MCP/general automation on port 9222 (StepPrompts lines ~35700, 35883). Cookies were SOPS-encrypted, synced, injected via CDP.
- After three architecture iterations (Obscura CDP → Camoufox → Playwright), browser automation was **abandoned** for P13 and replaced by Official X API v2 (`P13-028-ADR-Revision.md` ADR-2026-06-18-10). Reasons: unreliable DOM selectors, overlay/mask interference, session expiry after restart, high resource usage.
- **Lesson for P23:** browser automation is fragile for **posting/publishing** against adversarial DOMs. P23 should prefer browser automation for **read/extract/navigate/confirm** (lower risk, reversible) and route write/publish actions through official APIs where they exist (P22 pattern). Where browser write is unavoidable, it must be policy-gated (L2/L3), artifact-captured, and rollback-capable.

**Isolation precedent (port split):** the repo already enforces the isolation principle P23 needs — P13 used port 9223, MCP/general uses port 9222, so a P13 session cookie could never leak into a general browser action. P23 must preserve this: general P23 actions use port 9222 (or a dedicated P23 context on a separate port if stealth is ever needed — it is not, for general actions).

### 3.2 Playwright async API table (P23-relevant)

| API | Signature (async) | P23 use |
|---|---|---|
| `async_playwright()` | context manager / `.start()` | Entry point; `async with async_playwright() as p:` or `p = await async_playwright().start()` |
| `BrowserType.connect_over_cdp(endpoint, *, is_local, no_defaults, artifacts_dir)` | `await p.chromium.connect_over_cdp("ws://127.0.0.1:9222")` | **Primary path** — attach to Obscura CDP. `is_local=True` enables fs optimizations when same host. `no_defaults=True` avoids disturbing a user's browser state. `artifacts_dir` controls where traces/downloads land (v1.60+). |
| `BrowserType.launch(headless, ...)` | `await p.chromium.launch(headless=True)` | **Fallback path** — local headless Chromium when Obscura is down |
| `BrowserType.launch_persistent_context(user_data_dir, ...)` | `await p.chromium.launch_persistent_context("/path/to/profile")` | Persistent profile (cookies/localStorage across runs) — only for consented, scoped sessions; NOT general actions |
| `Browser.new_context(*, record_har_path, viewport, user_agent, storage_state, ...)` | `ctx = await browser.new_context(record_har_path="a.har.zip")` | **Per-action isolation** — clean-slate context; no shared cookies with other contexts; HAR recording via legacy option |
| `BrowserContext.new_page()` | `page = await ctx.new_page()` | New tab in the isolated context |
| `Page.goto(url, *, wait_until, timeout)` | `await page.goto(url, wait_until="networkidle", timeout=30000)` | Navigate; `wait_until` ∈ `commit|domcontentloaded|load|networkidle` (networkidle = no network for ≥500ms) |
| `Page.locator(selector)` | `btn = page.locator("text=Submit")` | **Recommended** — strict, auto-waiting, re-evaluated each call |
| `Locator.click(*, timeout)` | `await btn.click()` | Auto-waits for actionability (visible, enabled, stable) |
| `Page.click(selector)` (legacy) | `await page.click("#submit")` | Legacy; prefer `locator().click()` |
| `Locator.fill(value)` / `Page.fill(selector, value)` | `await page.locator("#email").fill("a@b.com")` | Set field value (replaces `page.type`, which is deprecated) |
| `Page.content()` | `html = await page.content()` | Full DOM HTML → DOM snapshot artifact / markdownify |
| `Page.title()` / `Page.url` | `await page.title()` / `page.url` | Metadata for audit |
| `Page.screenshot(*, full_page, path, mask, mask_color, type)` | `await page.screenshot(full_page=True, path="s.png", mask=[pw_loc])` | **Full-page screenshot artifact**; `mask` redacts sensitive elements with a pink box (#FF00FF) |
| `Page.wait_for_load_state(state, timeout)` | `await page.wait_for_load_state("networkidle")` | Wait for `load|domcontentloaded|networkidle` |
| `Page.wait_for_selector(selector, *, state, timeout)` | `await page.wait_for_selector("#x", state="visible", timeout=10000)` | Explicit wait; `state` ∈ `attached|detached|hidden|visible` |
| `Page.press(selector, key)` / `Locator.press(key)` | `await page.locator("input").press("Enter")` | Keyboard input |
| `Page.evaluate(expression)` | `val = await page.evaluate("document.title")` | JS extraction (scroll, custom extract) |
| `Page.mouse.wheel(dx, dy)` / `Page.mouse.move(x,y)` | `await page.mouse.wheel(0, 1000)` | Scroll |
| `Page.expect_download()` | `async with page.expect_download() as di: ...; d = await di.value` | **Download** primitive; `d.path()` / `d.save_as(path)` |
| `BrowserContext.tracing.start(snapshots, screenshots, sources, title)` | `await ctx.tracing.start(snapshots=True, screenshots=True, sources=True)` | **Trace** (actions + network + screenshots + DOM snapshots → zip) |
| `BrowserContext.tracing.stop(path)` | `await ctx.tracing.stop("trace.zip")` | Finalize trace |
| `BrowserContext.tracing.start_har(path, *, content, mode, url_filter)` / `stop_har()` | `await ctx.tracing.start_har("net.har.zip", content="attach")` | **HAR** (v1.60+ first-class; includes WebSocket in latest) |
| `BrowserContext.close()` / `Page.close()` | `await ctx.close()` | Rollback — destroys context, cookies, isolation boundary |

**Auto-waiting** (official https://playwright.dev/python/docs/actionability): Playwright auto-waits for actionability checks (visible, stable, enabled, receives events) before click/fill/hover. This removes most manual `sleep`/`wait` calls. For elements that may never appear, use `wait_for_selector(state="hidden")` or `locator.wait_for(state="detached")`.

**Network idle:** `wait_until="networkidle"` on `goto`, or `page.wait_for_load_state("networkidle")`, waits until there are no network connections for ≥500ms. For SPAs, prefer `domcontentloaded` + explicit `wait_for_selector` to avoid hanging on long-poll/WebSocket pages.

### 3.3 Action-primitive table (P23 browser executor)

Each primitive is policy-gated (PersonaSafetyPolicy §15.1 tool-risk gate + F-10 high-blast-radius check), audited (append-only hash-chained `audit.audit_tail` per P22 §3.2), artifact-captured, and rollback-capable.

| Primitive | Auth level | API | Rollback | Artifact |
|---|---|---|---|---|
| `navigate(url)` | L1 Read | `page.goto(url, wait_until="domcontentloaded")` | `page.go_back()` / close context | URL + title + timestamp + screenshot |
| `click(selector)` | L2 Write-Notify | `page.locator(sel).click()` | `page.go_back()` if navigation triggered; DOM snapshot diff | screenshot before/after + DOM snapshot |
| `fill(selector, value)` | L2 Write-Notify | `page.locator(sel).fill(value)` | restore previous value via `evaluate` or `page.go_back` (form reset); close context | redacted field name + masked value + screenshot |
| `extract_text(selector=None)` | L1 Read | `page.content()` + markdownify, or `locator.inner_text()` | n/a (read-only) | redacted markdown/text → artifact path |
| `screenshot(full_page=True)` | L1 Read | `page.screenshot(full_page=True, path=..., mask=[...])` | n/a | PNG artifact + `mask` redaction list |
| `scroll(dx, dy)` | L1 Read | `page.mouse.wheel(dx, dy)` | `page.evaluate("window.scrollTo(0,0)")` | n/a (or screenshot) |
| `wait(state, timeout)` | L1 Read | `page.wait_for_load_state(state)` / `wait_for_selector(sel, timeout)` | n/a | n/a |
| `download(url_or_trigger)` | L2 Write-Notify | `page.goto(url)` + `expect_download()` → `d.save_as(path)` | delete downloaded file | downloaded file path + hash + size |

**Rollback strategy:** every action opens a dedicated `BrowserContext` (isolation boundary). On failure or after action completion, `context.close()` destroys the context and all its cookies/localStorage — this is the primary rollback. For in-page mutations (fill, click-that-changes-DOM), capture a DOM snapshot (`page.content()`) before the action so a diff/restore is possible; for navigation-triggering actions, `page.go_back()` restores the previous page.

### 3.4 Isolation design

**Rule: dedicated context per action, separate process, no shared cookies across surfaces.**

1. **Per-action `BrowserContext`:** P23 must NOT reuse the current `obscura_cdp.py` singleton `Page`. Each P23 action creates a fresh `browser.new_context()` (clean-slate — no cookies, no localStorage inherited from other actions). Context is closed at action end. This is Playwright's canonical isolation model (https://playwright.dev/python/docs/browser-contexts: "Tests written with Playwright execute in isolated clean-slate environments called browser contexts").

2. **Port/instance separation by surface:**
   - Port 9222 = MCP/general browser automation (Obscura `--stealth` off for general actions is acceptable; stealth is a P13-only consented need).
   - Port 9223 = P13 X Auto Poster (if ever re-enabled; currently abandoned).
   - P23 general actions use port 9222 but with **per-action contexts** so they cannot read P13 cookies even if P13 were running.
   - If P23 ever needs a stealth/consented persistent session (e.g., a logged-in service the user consented to), it gets its **own port + own persistent context (`launch_persistent_context` with a dedicated `user_data_dir`)**, never sharing with general actions or P13.

3. **Stealth is NOT for general actions:** ADR-033 enables `--stealth` globally on the Obscura server because P13 needed anti-detect. For P23 general actions (navigate, extract, screenshot), stealth is unnecessary and potentially deceptive — P23 is acting openly as Guinevere on the user's behalf. **Recommendation:** split the Obscura server config so stealth applies only to the P13-consented port, OR run a second non-stealth Obscura instance for general P23 actions. If a single server must stay stealth, document that general actions inherit stealth by default and that this is acceptable only because it avoids bot-detection false positives on read-only public pages.

4. **Process isolation:** P23 browser actions execute in the MCP server process (or a dedicated `guinevere-browser` worker). The Obscura CDP server is a separate systemd service. A P23 action crashing the page/context does not crash Obscura or the MCP server.

5. **No shared cookies across surfaces:** per-action `new_context()` has no cookies. Persistent contexts (if any) are scoped to one integration + one `user_data_dir` + one port. Cross-surface cookie leakage is structurally impossible.

### 3.5 Artifact model

Every P23 browser action that captures content produces an **artifact bundle** at a deterministic path:

```
artifacts/p23/browser/<action_id>/
  ├── screenshot_full.png      # page.screenshot(full_page=True, mask=[...])
  ├── dom_snapshot.html        # page.content() at action end
  ├── network.har.zip          # ctx.tracing.start_har(...) / stop_har() OR record_har_path
  ├── trace.zip                # ctx.tracing.start(snapshots=True, screenshots=True) / stop
  ├── metadata.json            # action_id, url, title, ts, selector, auth_level, principal, redaction_applied
  └── extracted.md             # markdownify(dom_snapshot) with PII/secrets redacted
```

**Redaction (mandatory before persistence):**
- Run `src/surveillance/secret_scanner.py` (existing, per P21 §Prompt-Injection Handling) on all captured text (DOM, extracted markdown, HAR bodies).
- Redact secrets (tokens, keys, passwords) → drop/hash-only.
- Redact PII (email, phone, national ID) → mask or hash.
- For screenshots, use `page.screenshot(mask=[locator_email, locator_token])` to overlay sensitive elements with a pink box before the PNG is written (official https://playwright.dev/python/docs/api/class-page).
- HAR `content` policy: use `omit` for sensitive pages (no response bodies persisted) or `attach` + post-process redaction for diagnostics.
- Classification per P22 §6.2 / P21 retention: browser-captured screen content = **CRITICAL** (surveillance-class — it captures what is on screen, which may include private messages, credentials, financial data). Retention: raw screenshot/HAR ≤24h unless incident hold; redacted extracted text = Restricted/Long-Term Curated; safe-word/intimate content = Critical + `do_not_recall`.

**Artifact path registration:** the `metadata.json` + a content hash are written to `audit.audit_tail` (P22 §3.2 schema: `event_id`, `actor_id`, `endpoint_path`, `data_volume_bytes`, `event_hash`, `previous_hash`). This makes artifacts tamper-evident and forensically traceable.

### 3.6 Failure modes + self-debug

| Failure mode | Detection | Mitigation | Self-debug (HermesBrain) |
|---|---|---|---|
| Navigation timeout (30s) | `page.goto` raises `TimeoutError` | Retry once with `wait_until="domcontentloaded"` (less strict than networkidle); fall back to `extract_text` on partial content; log + screenshot partial | HermesBrain receives the error + partial screenshot; planner can re-plan with a different URL/selector or mark the goal blocked |
| Element not found (selector miss) | `wait_for_selector`/`locator.click` raises `Error` after timeout | Capture DOM snapshot + screenshot; search for alternative selectors via `page.locator("text=...")`; if still missing, surface to planner | HermesBrain diffs the DOM snapshot against expected structure; suggests revised selector or alternative action path |
| CDP disconnect (Obscura crash/restart) | `connect_over_cdp` raises `ConnectionRefusedError`/`OSError` | tenacity retry (3×, 2s) in `obscura_cdp.py` pattern; if still failing, **fall back to `p.chromium.launch(headless=True)`** (Playwright+Chromium, ADR-020 fallback); raise `ObscuraNotRunning` with start command | HermesBrain receives `ObscuraNotRunning`; can trigger `systemctl restart guinevere-obscura` (if L3-approved) or route the action to the local Chromium fallback |
| Rate-limit / 403 / bot-detection | HTTP 403/429 in HAR or `page.url` redirect to challenge | Honor `Retry-After`; exponential backoff with jitter (P22 §5.3); if repeated, mark the domain as bot-protected and surface to planner | HermesBrain logs the 403 pattern; may switch user-agent via `new_context(user_agent=...)` or escalate to a consented stealth context (L3 approval) |
| Page hang (SPA long-poll) | `wait_for_load_state("networkidle")` never resolves | Switch to `domcontentloaded` + explicit `wait_for_selector` for the target element; set hard timeout | HermesBrain identifies long-poll domains and adjusts the wait strategy for future actions |
| Form-fill value rejected | Field validation error visible after `fill` | Screenshot the error; surface to planner; do not retry blindly | HermesBrain reads the validation error text from the DOM snapshot; revises the value or asks the user |
| Download incomplete | `expect_download()` timeout | Retry once; verify file size/hash; if partial, delete + re-trigger | HermesBrain checks `d.path()` + expected size; re-plans |

**Self-debug loop:** every failure produces an artifact bundle (screenshot + DOM + error). HermesBrain (`src/hermes/`) receives a structured failure event with the artifact path. The planner (P23 action planner, LLM via 9Router) reads the redacted screenshot/DOM, diagnoses, and either re-plans (revised selector/URL/strategy), escalates to a higher auth level (L3 Faiz approval), or marks the goal blocked + notifies via Discord. This is the same HermesBrain self-improvement loop used by the life_kernel (P20) and P21 voice — no new debug infrastructure.

### 3.7 Consent + classification

**Consent scope: `p23:browser`** (per P22 §2.1 granular per-scope consent model).

| Sub-scope | Operation class | Guinevere level | Consent behavior |
|---|---|---|---|
| `p23:browser.navigate` | Read | L1 Read-Autonomous | Pre-authorizable for allowlisted public domains; logged, no per-action prompt |
| `p23:browser.extract` | Read | L1 | Pre-authorizable; redacted text only |
| `p23:browser.screenshot` | Read (surveillance-class) | L1 + surveillance gate | Captures screen content → CRITICAL classification; 24h raw retention; redacted extract persists longer |
| `p23:browser.click` | Write | L2 Write-Notify | Notify after action; requires prior scope consent |
| `p23:browser.fill` | Write | L2 | Notify after; field value redacted in audit |
| `p23:browser.download` | Write | L2 | Notify; file hash + size logged |
| `p23:browser.persistent_session` | Write (logged-in) | L3 Destructive-Approval | Explicit per-action approval for any logged-in/persistent session; never auto-enabled |
| `p23:browser.stealth` | Write (deceptive) | L3/L4 | Stealth only for P13-consented posting (abandoned); general stealth = L4 Forbidden unless Faiz explicitly approves a specific consented action |

**Surveillance classification (per P21 §Retention/Redaction + P22 §6):** browser screenshots/HAR/DOM capture **screen content**, which is surveillance-class (may include private messages, credentials, financial data, intimate content). Consequences:
- Raw artifacts = CRITICAL, retention ≤24h (Short Raw, auto-delete unless incident hold), `envelope-AES-256-GCM` (double for Critical).
- Redacted extracted text = Restricted, long-term curated.
- Safe-word/intimate content captured = Critical + `do_not_recall=true` + double-encrypt.
- Consent revocation cascade (P21 A8 pattern): revoke `p23:browser.*` → mark browser artifacts `deletion_state='pending_delete'` → purge raw screenshots/HAR → record cascade in `consent.revocation_log.cascade_effects`.
- Fail-closed consent cache (P21 pattern): if consent cache is unavailable, browser actions are BLOCKED, not allowed.

**F-10 (Irreversible action under persona pressure) interaction:** browser write actions (click, fill, download) can be irreversible (e.g., clicking "Delete account", submitting a payment). The tool-risk gate (§15.1) + F-10 high-blast-radius check MUST run before every L2/L3 browser write. If the persona is under pressure (yandere intensity high, distress, or prompt-injection suspicion), browser writes are blocked and require Faiz approval.

### 3.8 Local fallback

Per ADR-020 + ADR-033 Rollback Plan:
- If `guinevere-obscura.service` is down (`connect_over_cdp` fails after 3 retries), P23 falls back to `p.chromium.launch(headless=True)` (full Playwright + Chromium).
- Fallback triggers: Obscura crash, Obscura CDP coverage gap (e.g., `Page.captureScreenshot` not implemented → use Chromium for screenshot actions), Obscura upgrade/restart.
- Fallback cost: ~300MB binary, ~200MB RAM (vs 30MB Obscura) — acceptable on the 8GB Guinevere allocation for short bursts.
- Fallback limitation: no built-in stealth (irrelevant for general P23 actions; only matters for P13-consented posting, which is abandoned).
- Rollback time (Obscura → Chromium and back): <5 minutes per ADR-033.
- P23 implementation: the `obscura_cdp.py` `_BrowserState.ensure_connected()` pattern already raises `ObscuraNotRunning` with the fallback command. P23 wraps this: try Obscura `connect_over_cdp` → on `ObscuraNotRunning`, `launch(headless=True)` Chromium + log the fallback + metric `browser_fallback_total`.

### 3.9 Cost model

| Component | Cost |
|---|---|
| Obscura CDP server (browser runtime) | $0 (Apache-2.0, self-hosted) |
| Playwright + Chromium fallback | $0 (open source, self-hosted) |
| Browser action execution (CPU/RAM on VPS) | $0 (within existing 4C/16GB VPS allocation; Obscura ~30MB, Chromium ~200MB per burst) |
| LLM — action planner (9Router GPT-5.5 / DeepSeek V4 Flash) | ~$0.002-0.005 per action (plan + selector selection) |
| LLM — text extraction/summarization (Hermes via 9Router) | ~$0.002-0.005 per extract (redact + summarize DOM) |
| Screenshot/HAR/trace storage | negligible (artifacts ≤24h raw; redacted extracts small) |

**Total per browser action:** ~$0.004-0.01 (dominated by LLM, not browser). **Browser itself: $0.** This aligns with the P13 cost note (`70-Cost_FinOps_Model_v1.1.md`: Obscura CDP $0) and the P21 cost model (LLM is the bottleneck, not the substrate). Budget cap: feeds existing `CostTracker` with model tags `browser:planner` / `browser:extract`; included in the existing USD 30/mo system cap.

## 4. Implications for P23 Design

1. **Do NOT build a parallel browser stack.** Extend the existing `src/mcp/tools/obscura_cdp.py` + Obscura CDP server (port 9222). P23 adds: per-action `BrowserContext`, artifact capture (screenshot/DOM/HAR/trace), redaction, policy gate, audit, consent, and the local Chromium fallback. The current 4 tools (navigate/get_markdown/fill_form/click) become the base layer; P23 wraps them with isolation + audit + artifacts.

2. **Per-action context is mandatory.** The singleton `Page` in `obscura_cdp.py` is a P23 blocker. Refactor to `browser.new_context()` per action, close on completion. This is the single most important isolation change.

3. **Pixel rendering gap.** `obscura_cdp.py` says "No `page.screenshot()` — Obscura has no pixel rendering." P23 needs screenshots. Options: (a) verify Obscura now supports `Page.captureScreenshot` CDP domain (re-test; ADR-033 said 9/40+ domains as of June 2026); (b) use the Playwright+Chromium fallback specifically for screenshot/artifact actions while using Obscura for navigate/extract; (c) run Obscura for stealth/read and Chromium for capture. **Recommendation:** test Obscura screenshot support first; if absent, route screenshot/DOM/HAR capture to the Chromium fallback automatically.

4. **Two-tier action routing (read vs. write).** Read actions (navigate, extract, screenshot, scroll, wait) = L1, lower risk, Obscura-primary. Write actions (click, fill, download) = L2/L3, higher risk, policy-gated, artifact-captured, rollback-capable. P13's failure teaches: prefer official APIs for publish/post; use browser only when no API exists.

5. **Reuse P22 consent/audit/secret infrastructure verbatim.** `p23:browser.*` consent scopes into the existing `consent.consent_ledger`; audit events into `audit.audit_tail` (hash-chained, append-only); secrets (any persistent session cookies/tokens) into SOPS/age + Fernet field-level encryption. Do not build new consent/audit/secret code.

6. **Reuse P21 surveillance-class patterns.** Screen capture = CRITICAL, 24h raw retention, redaction before persistence, fail-closed consent cache, consent-revocation cascade, `do_not_recall` on intimate/safe-word content. P21 already designed this for voice raw audio; P23 applies the same classification to browser screenshots/HAR.

7. **HermesBrain self-debug, not a new debugger.** Browser failures produce artifact bundles; HermesBrain reads them and re-plans. This is the P20 life_kernel + P21 voice pattern — no new debug infrastructure.

8. **Systemd service.** `guinevere-obscura.service` already exists. P23 does not need a new service unless it wants a dedicated `guinevere-browser` worker (recommended if browser actions are long-running and could block the MCP server). If added, mirror the P21 `guinevere-voice` isolation pattern (`MemoryLimit`, `CPUQuota`, `After=guinevere-core.service`, no `Requires=`).

9. **Feature flag + kill switch.** `browser.enabled:false` config flag (P21 pattern); `/browser-off` Discord kill switch (Faiz-only); HARD STOP halts browser actions (spoken/typed safe word → Redis `life_kernel:hard_stop` → browser actions check it pre-action and abort).

## 5. Risks / Open Questions

| # | Risk / Question | Severity | Mitigation / Resolution path |
|---|---|---|---|
| R1 | Obscura CDP coverage gap (screenshots/tracing/HAR not in the 9/40+ implemented domains) | HIGH | Test Obscura `Page.captureScreenshot` + Tracing support on the live VPS first. If absent, auto-route capture actions to Chromium fallback. |
| R2 | P13 taught that browser automation is fragile for adversarial DOMs (posting). P23 general actions may hit the same fragility (SPAs, overlays, bot-detection) | MEDIUM | Prefer read/extract over write; prefer official APIs (P22) for publish; artifact-capture every action so HermesBrain can self-debug; domain allowlist + bot-detection fallback. |
| R3 | Stealth enabled globally on Obscura (ADR-033 `--stealth`) — is that appropriate for general P23 read actions? | LOW-MEDIUM | Document that general actions inherit stealth; acceptable for read-only public pages; for consented logged-in sessions, use a dedicated persistent context + port. If concerning, split stealth to P13-port only. |
| R4 | Per-action `new_context()` has overhead (~50-200ms context creation) — acceptable for P23's expected action volume? | LOW | P23 is single-user, low-volume (personal OS actions, not scraping). Context creation overhead is negligible vs. LLM planner latency. |
| R5 | HAR/screenshot artifacts may capture credentials/PII if redaction masks are incomplete | HIGH | Mandatory `secret_scanner.py` pass on all text; `page.screenshot(mask=[...])` for known sensitive locators; HAR `content=omit` for sensitive domains; 24h raw retention + auto-purge; CRITICAL classification. |
| R6 | F-10: browser write action under persona pressure could be irreversible (e.g., "Delete account" click) | CRITICAL | Tool-risk gate (§15.1) + F-10 high-blast-radius check before every L2/L3 browser write; block under persona pressure; require Faiz approval for destructive clicks. |
| R7 | Persistent logged-in sessions (banking, email) — how are credentials stored? | MEDIUM | SOPS/age encrypted cookies/tokens; Fernet field-level encryption at rest; per-integration `user_data_dir` + port; L3 per-action approval; consent revocation cascade. |
| R8 | Obscura pre-1.0, bus-factor, self-reported benchmarks | MEDIUM | Playwright+Chromium fallback is documented and <5min rollback; monitor Obscura releases; test CDP coverage before each P23 release. |
| R9 | Does P23 need a dedicated `guinevere-browser` systemd worker, or run in the MCP server process? | LOW | Start in MCP process (simpler); split to a worker if browser actions block MCP or resource ceiling is hit. Mirror P21 `guinevere-voice` isolation if split. |
| R10 | Consent scope granularity — is `p23:browser.navigate` per-domain or global? | LOW | Per-domain allowlist for L1 navigate (public sites auto-allowed, sensitive domains require explicit consent); global `p23:browser.*` for the category + per-domain rows in `consent_ledger`. |

## 6. Recommendations to Planner

1. **Base layer:** extend `src/mcp/tools/obscura_cdp.py` into a `src/browser/` package (or `src/p23/browser_executor.py`) that wraps the existing 4 primitives with: per-action `BrowserContext`, artifact capture, redaction, policy gate, audit, consent. Do NOT fork a new browser stack.

2. **Isolation refactor (critical):** replace the singleton `_BrowserState.page` with a `BrowserContext`-per-action manager. `new_context()` on action start, `close()` on action end (success or failure). This is the structural isolation boundary.

3. **Screenshot/artifact capture:** test Obscura `Page.captureScreenshot` + Tracing first. If unsupported, auto-fallback to `p.chromium.launch(headless=True)` for capture actions only. Standard artifact bundle: `screenshot_full.png` + `dom_snapshot.html` + `network.har.zip` + `trace.zip` + `metadata.json` + `extracted.md` at `artifacts/p23/browser/<action_id>/`.

4. **Redaction pipeline:** run `src/surveillance/secret_scanner.py` on all captured text; use `page.screenshot(mask=[...])` for sensitive locators; HAR `content=omit` for sensitive domains. Classification = CRITICAL (surveillance-class), 24h raw retention, `envelope-AES-256-GCM`.

5. **Consent:** `p23:browser.*` scopes in `consent.consent_ledger`; per-domain allowlist for L1 navigate; L2/L3 for write/persistent; fail-closed consent cache (P21 pattern); consent-revocation cascade (P21 A8 pattern).

6. **Policy gate:** every browser action passes the §15.1 tool-risk gate + F-10 high-blast-radius check before execution. Under persona pressure (yandere high / distress / injection suspicion), L2/L3 writes are blocked, require Faiz approval. HARD STOP (Redis `life_kernel:hard_stop`) is checked pre-action and aborts.

7. **Audit:** every action → `audit.audit_tail` (P22 §3.2 schema, hash-chained, append-only). Fields: `actor_id`, `endpoint_path` (URL), `http_method` (navigate/click/fill), `scope_used`, `response_status`, `data_volume_bytes`, `correlation_id`, `event_hash`, `previous_hash`. No tokens/PII in audit rows.

8. **Failure/self-debug:** every failure produces an artifact bundle; HermesBrain receives a structured failure event with the artifact path; planner re-plans or escalates. Metrics: `browser_action_total`, `browser_action_failed_total`, `browser_fallback_total`, `browser_action_latency_seconds`, `browser_consent_violation_total`.

9. **Fallback:** try Obscura `connect_over_cdp` (3 retries) → on `ObscuraNotRunning`, `launch(headless=True)` Chromium + log + metric. <5min rollback per ADR-033.

10. **Cost:** tag LLM calls `browser:planner` / `browser:extract` in `CostTracker`; browser runtime $0; per-action ~$0.004-0.01 (LLM-dominated); within USD 30/mo system cap.

11. **Systemd:** if a dedicated worker is warranted, mirror P21 `guinevere-voice` (`MemoryLimit=512M`, `CPUQuota`, `After=guinevere-core.service`, no `Requires=`, feature flag `browser.enabled`, `/browser-off` kill switch).

12. **Two-tier routing:** read actions (navigate/extract/screenshot/scroll/wait) = L1, Obscura-primary, lower artifact burden. Write actions (click/fill/download) = L2/L3, policy-gated, full artifact + rollback. Prefer official APIs (P22) for publish/post; browser write only when no API exists.

## 7. Verdict

**PROCEED with P23 browser automation design on the existing Obscura CDP + Playwright stack.** The repo already has a deployed, systemd-managed Obscura CDP server (port 9222) and a working Playwright client (`src/mcp/tools/obscura_cdp.py`). P23 extends this base with per-action context isolation, artifact capture (screenshot/DOM/HAR/trace), redaction, policy-gated consent, hash-chained audit, and a documented Chromium fallback — reusing P22 (consent/audit/secrets) and P21 (surveillance-class retention/redaction/HARD STOP) infrastructure verbatim. The P13 browser-abandonment lesson is absorbed: browser automation is for read/extract/confirm, not adversarial posting. The single highest-risk open item is R1 (Obscura CDP screenshot/tracing coverage) — resolve by live test before the planner finalizes the capture path; auto-fallback to Chromium is the documented escape hatch. Browser runtime cost is $0; LLM planner/extract cost (~$0.004-0.01/action) is the only variable cost and fits the existing cap. No new ADR is required; ADR-020 + ADR-033 remain authoritative. Implementation should be gated behind `browser.enabled:false` + `/browser-off` kill switch and blocked on a fresh preflight runtime incident check before any life_kernel/hermes_brain LOCKED-file edits (P20 axis satisfied by operator accepted-risk waiver 2026-06-25; P21 non-interference contract).

**Output path:** `docs/setup-evidence/P23/research/p23-browser-automation-research.md`

**Summary:** Mapped existing Obscura CDP (port 9222, `guinevere-obscura.service`) + Playwright client (`obscura_cdp.py`, 4 tools, singleton Page — P23 must refactor to per-action `BrowserContext`). Distilled Playwright async API (connect_over_cdp primary, launch fallback, locators, auto-waiting, networkidle, tracing/HAR/video, screenshot with mask). Defined 8 policy-gated action primitives with rollback. P13 abandonment lesson: browser for read/extract, APIs for publish. Surveillance-class (CRITICAL, 24h raw, redaction mandatory). Reuses P22 consent/audit + P21 retention/HARD STOP. Cost $0 browser, ~$0.004-0.01/action LLM. Chromium fallback <5min.
