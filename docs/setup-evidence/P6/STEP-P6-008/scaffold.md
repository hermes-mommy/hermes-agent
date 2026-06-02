# Scaffold: STEP-P6-008 — grep_app

## Expected Files

- `src/mcp/tools/grep_app.py` — Code search tool via grep.app API
- `tests/mcp/test_grep_app.py` — Unit tests with mocked httpx responses

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
| `python -m pytest tests/mcp/test_grep_app.py -v` | 0 | All tests pass |
| `python -m ruff check src/mcp/tools/grep_app.py` | 0 | No lint errors |
| `python -m mypy src/mcp/tools/grep_app.py` | 0 | No type errors |

## Implementation Details

### Key Design

- **HTTP Client:** `httpx.AsyncClient` with timeout=15s
- **API Endpoint:** `https://grep.app/api/search` (GET)
- **Auth:** None required (public API)
- **Auth Level:** `AuthLevel.READ_AUTO`
- **Cost:** $0
- **Parameters:** `q` (query), `regexp` (bool), `lang` (language filter), `repo` (repo filter), `path` (path filter)
- **Return:** List of code snippets with repo, path, line content

### Function Signature

```python
async def grep_app_search(
    query: str,
    language: list[str] | None = None,
    repo: str | None = None,
    use_regexp: bool = False,
    match_case: bool = True,
) -> list[dict[str, str]]:
    """Search for real-world code patterns across GitHub via grep.app."""
```

### Error Handling

- Network error → log + return empty list
- Empty results → return empty list (not an error)
- Rate limit (if any) → log + backoff + retry once

## Evidence Requirements

- `docs/setup-evidence/P6/STEP-P6-008/verification.md` — 12-section verification report
- `docs/setup-evidence/P6/STEP-P6-008/auditor-gate.md` — auditor verdict

## Hard Rejection Criteria

- [ ] All expected files exist
- [ ] All forbidden patterns return zero matches
- [ ] All required commands pass (exit 0)
- [ ] Evidence files exist and are non-empty
- [ ] No API keys in source file (grep.app requires no auth)
- [ ] Auth level `READ_AUTO` enforced
- [ ] `httpx.AsyncClient` used
- [ ] `structlog` used for all logging
- [ ] Tests use mocked httpx responses
- [ ] Language filter and regex parameters supported
