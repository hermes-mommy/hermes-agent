# Scaffold: STEP-P6-003 — context7

## Expected Files

- `src/mcp/tools/context7.py` — Context7 library documentation lookup tool
- `tests/mcp/test_context7.py` — Unit tests with mocked HTTP responses

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

## Required Commands

| Command | Expected Exit Code | Notes |
|---------|-------------------|-------|
| `python -m pytest tests/mcp/test_context7.py -v` | 0 | All tests pass |
| `python -m ruff check src/mcp/tools/context7.py` | 0 | No lint errors |
| `python -m mypy src/mcp/tools/context7.py` | 0 | No type errors |

## Implementation Details

### Key Design

- **HTTP Client:** `httpx.AsyncClient` with timeout=15s
- **API:** Context7 REST API — resolve library ID, then query documentation
- **Auth Level:** `AuthLevel.READ_AUTO` — no approval needed
- **Cost:** Free (1000 calls/month limit)
- **Caching:** In-memory LRU cache to stay within 1000 calls/month
- **Return:** Library ID, name, description, code snippets

### Function Signatures

```python
async def context7_resolve(library_name: str, query: str = "") -> dict[str, str]:
    """Resolve a library name to a Context7 library ID."""

async def context7_query(library_id: str, query: str) -> dict[str, object]:
    """Query documentation for a resolved library."""
```

### Error Handling

- Library not found → return empty dict with suggestion
- Rate limit exceeded (429) → log + return cached result or empty
- Network error → log + raise with retry suggestion

## Evidence Requirements

- `docs/setup-evidence/P6/STEP-P6-003/verification.md` — 12-section verification report
- `docs/setup-evidence/P6/STEP-P6-003/auditor-gate.md` — auditor verdict

## Hard Rejection Criteria

- [ ] All expected files exist
- [ ] All forbidden patterns return zero matches
- [ ] All required commands pass (exit 0)
- [ ] Evidence files exist and are non-empty
- [ ] No API keys in source file (Context7 free tier requires no key)
- [ ] Auth level `READ_AUTO` enforced
- [ ] `httpx.AsyncClient` used
- [ ] `structlog` used for all logging
- [ ] LRU cache implemented for rate limit protection
- [ ] Tests use mocked HTTP responses
