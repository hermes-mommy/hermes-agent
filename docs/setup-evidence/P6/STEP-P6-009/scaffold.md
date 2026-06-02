# Scaffold: STEP-P6-009 — obscura_cdp (Playwright via Obscura CDP)

## Expected Files

- `src/mcp/tools/obscura_cdp.py` — Browser automation via Obscura CDP + Playwright
- `systemd/guinevere-obscura.service` — systemd unit for Obscura CDP server
- `tests/mcp/test_obscura_cdp.py` — Unit tests with mocked playwright

## Forbidden Patterns

- `as any`
- `@ts-ignore`
- `# type: ignore`
- `cast(`
- `except Exception:` (empty/swallowed)
- `except:` (bare)
- `page.screenshot(` — **CRITICAL: No screenshot support via Playwright**
- `playwright-core` as pip package — use `pip install playwright` with `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1`
- `print(` (use structlog)
- `import logging` (use structlog)
- `selenium` (use Playwright)

## Required Commands

| Command | Expected Exit Code | Notes |
|---------|-------------------|-------|
| `python -m pytest tests/mcp/test_obscura_cdp.py -v` | 0 | All tests pass |
| `python -m ruff check src/mcp/tools/obscura_cdp.py` | 0 | No lint errors |
| `python -m mypy src/mcp/tools/obscura_cdp.py` | 0 | No type errors |
| `grep -r "screenshot" src/mcp/tools/obscura_cdp.py` | 1 | No screenshot calls found |
| `grep -r "playwright-core" pyproject.toml` | 1 | No playwright-core in deps |

## Implementation Details

### Key Design (ADR-033)

- **CDP Connection:** `connect_over_cdp("ws://127.0.0.1:9222")`
- **Content Extraction:** `page.content()` or evaluate `LP.getMarkdown` — NOT `page.screenshot()`
- **Auth Levels:**
  - Navigate/read page → `AuthLevel.READ_AUTO`
  - Form fill/click → `AuthLevel.WRITE_NOTIFY`
  - File upload/cookie manipulation → `AuthLevel.DESTRUCTIVE_APPROVAL`
- **Cost:** $0
- **Obscura Binary:** `/usr/local/bin/obscura serve --port 9222 --stealth --workers 2`
- **Pip:** `pip install playwright` with `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1`

### Function Signatures

```python
async def obscura_navigate(url: str) -> dict[str, str]:
    """Navigate to URL and return page title + content. Auth: READ_AUTO."""

async def obscura_get_markdown(url: str) -> str:
    """Navigate and extract markdown content. Auth: READ_AUTO."""

async def obscura_fill_form(url: str, selectors: dict[str, str]) -> dict[str, str]:
    """Fill form fields on page. Auth: WRITE_NOTIFY."""

async def obscura_click(selector: str) -> dict[str, str]:
    """Click element on current page. Auth: WRITE_NOTIFY."""
```

### CRITICAL: No Screenshot

Per ADR-033, `page.screenshot()` is NOT supported in the Obscura CDP integration. Use:
- `page.content()` — returns raw HTML
- `page.evaluate("LP.getMarkdown")` — returns markdown (if LP available)
- `page.title()` — returns page title

### systemd Service

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

### Error Handling

- CDP connection refused → log + raise with "Obscura not running on port 9222"
- Page load timeout → log + return partial content
- Selector not found → log + raise `ElementNotFoundError`

## Evidence Requirements

- `docs/setup-evidence/P6/STEP-P6-009/verification.md` — 12-section verification report
- `docs/setup-evidence/P6/STEP-P6-009/auditor-gate.md` — auditor verdict

## Hard Rejection Criteria

- [ ] All expected files exist
- [ ] All forbidden patterns return zero matches
- [ ] All required commands pass (exit 0)
- [ ] Evidence files exist and are non-empty
- [ ] **ZERO `page.screenshot()` calls in source**
- [ ] `connect_over_cdp("ws://127.0.0.1:9222")` used for connection
- [ ] `page.content()` or `LP.getMarkdown` used for content extraction
- [ ] Three auth levels enforced per operation type
- [ ] systemd service specifies `--stealth --workers 2`
- [ ] `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1` documented in install instructions
- [ ] `structlog` used for all logging
- [ ] Tests mock playwright browser/page objects
