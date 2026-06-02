# Scaffold: STEP-P6-005 — fetch

## Expected Files

- `src/mcp/tools/fetch.py` — Web content retrieval tool (HTTP GET + markdownify)
- `tests/mcp/test_fetch.py` — Unit tests with mocked httpx responses

## Forbidden Patterns

- `as any`
- `@ts-ignore`
- `# type: ignore`
- `cast(`
- `except Exception:` (empty/swallowed)
- `except:` (bare)
- Hardcoded API keys
- `print(` (use structlog)
- `import logging` (use structlog)
- `requests.` (use httpx)
- `urllib` (use httpx)

## Required Commands

| Command | Expected Exit Code | Notes |
|---------|-------------------|-------|
| `python -m pytest tests/mcp/test_fetch.py -v` | 0 | All tests pass |
| `python -m ruff check src/mcp/tools/fetch.py` | 0 | No lint errors |
| `python -m mypy src/mcp/tools/fetch.py` | 0 | No type errors |

## Implementation Details

### Key Design

- **HTTP Client:** `httpx.AsyncClient` with timeout=30s, follow_redirects=True
- **Conversion:** `markdownify` library for HTML→Markdown conversion
- **Auth Level:** `AuthLevel.READ_AUTO`
- **Cost:** $0 (no API key required)
- **Max Content Size:** 1MB response body limit
- **Return:** Markdown string with metadata (title, URL, content length)

### Function Signature

```python
async def fetch_url(url: str, format: str = "markdown") -> dict[str, str]:
    """Fetch a URL and return content as markdown or text."""
```

### Security

- URL validation: reject `file://`, `ftp://`, non-HTTP(S) schemes
- Redirect following: max 5 redirects
- Content-Type check: only process text/html, application/json
- Response size limit: 1MB via httpx `max_content` parameter

### Error Handling

- Invalid URL scheme → raise `ValueError` with explanation
- HTTP error (4xx/5xx) → log + return error dict
- Timeout → log + raise with URL context
- Non-HTML content → return raw text with content-type warning

## Evidence Requirements

- `docs/setup-evidence/P6/STEP-P6-005/verification.md` — 12-section verification report
- `docs/setup-evidence/P6/STEP-P6-005/auditor-gate.md` — auditor verdict

## Hard Rejection Criteria

- [ ] All expected files exist
- [ ] All forbidden patterns return zero matches
- [ ] All required commands pass (exit 0)
- [ ] Evidence files exist and are non-empty
- [ ] No API keys in source file (fetch requires no auth)
- [ ] Auth level `READ_AUTO` enforced
- [ ] `httpx.AsyncClient` used (not `requests` or `urllib`)
- [ ] `markdownify` used for HTML→Markdown conversion
- [ ] URL scheme validation rejects non-HTTP(S) URLs
- [ ] Response size limit enforced (1MB)
- [ ] `structlog` used for all logging
- [ ] Tests use mocked httpx responses
