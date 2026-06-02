# Scaffold: STEP-P6-002 — brave_search

## Expected Files

- `src/mcp/tools/brave_search.py` — Brave Search MCP tool implementation
- `tests/mcp/test_brave_search.py` — Unit tests with mocked httpx responses

## Forbidden Patterns

- `as any`
- `@ts-ignore`
- `# type: ignore`
- `cast(`
- `except Exception:` (empty/swallowed)
- `except:` (bare)
- Hardcoded API keys (must use `os.environ["BRAVE_API_KEY"]` or SOPS decryption)
- `print(` (use structlog)
- `import logging` (use structlog)
- `requests.` (use httpx)

## Required Commands

| Command | Expected Exit Code | Notes |
|---------|-------------------|-------|
| `python -m pytest tests/mcp/test_brave_search.py -v` | 0 | All tests pass |
| `python -m ruff check src/mcp/tools/brave_search.py` | 0 | No lint errors |
| `python -m mypy src/mcp/tools/brave_search.py` | 0 | No type errors |

## Implementation Details

### Key Design

- **HTTP Client:** `httpx.AsyncClient` with timeout=10s, retries via tenacity
- **API Endpoint:** `https://api.search.brave.com/res/v1/web/search`
- **Auth Header:** `X-Subscription-Token` from environment variable `BRAVE_API_KEY`
- **Auth Level:** `AuthLevel.READ_AUTO` — no approval needed
- **Cost:** ~$0.01/search, tracked in Redis DB5
- **Rate Limit:** 2000 req/month (free tier)
- **Return:** List of dicts with `title`, `url`, `description`

### Function Signature

```python
async def brave_search(query: str, count: int = 5) -> list[dict[str, str]]:
    """Search the web via Brave Search API."""
```

### Error Handling

- `httpx.HTTPStatusError` → log + return empty list with error context
- `httpx.ConnectError` → log + raise with retry suggestion
- Missing `BRAVE_API_KEY` → raise `ConfigurationError` at import time

## Evidence Requirements

- `docs/setup-evidence/P6/STEP-P6-002/verification.md` — 12-section verification report
- `docs/setup-evidence/P6/STEP-P6-002/auditor-gate.md` — auditor verdict

## Hard Rejection Criteria

- [ ] All expected files exist
- [ ] All forbidden patterns return zero matches
- [ ] All required commands pass (exit 0)
- [ ] Evidence files exist and are non-empty
- [ ] No API keys in source file — `BRAVE_API_KEY` read from `os.environ` only
- [ ] Auth level `READ_AUTO` enforced via `@require_approval(AuthLevel.READ_AUTO)`
- [ ] `httpx.AsyncClient` used (not `requests` or `aiohttp`)
- [ ] `structlog` used for all logging
- [ ] Tests use mocked httpx responses (no live API calls in tests)
- [ ] Cost tracking call to Redis DB5 on each search
