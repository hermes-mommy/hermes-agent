# Scaffold: STEP-P6-007 — github

## Expected Files

- `src/mcp/tools/github.py` — GitHub API tool (repos, issues, PRs, code search)
- `tests/mcp/test_github.py` — Unit tests with mocked httpx responses

## Forbidden Patterns

- `as any`
- `@ts-ignore`
- `# type: ignore`
- `cast(`
- `except Exception:` (empty/swallowed)
- `except:` (bare)
- Hardcoded PAT or tokens (must use `os.environ["GITHUB_PAT"]` or SOPS)
- `print(` (use structlog)
- `import logging` (use structlog)
- `requests.` (use httpx)
- `PyGithub` or `github3.py` (use direct httpx to REST API)

## Required Commands

| Command | Expected Exit Code | Notes |
|---------|-------------------|-------|
| `python -m pytest tests/mcp/test_github.py -v` | 0 | All tests pass |
| `python -m ruff check src/mcp/tools/github.py` | 0 | No lint errors |
| `python -m mypy src/mcp/tools/github.py` | 0 | No type errors |

## Implementation Details

### Key Design

- **HTTP Client:** `httpx.AsyncClient` with `base_url="https://api.github.com"`, timeout=15s
- **Auth Header:** `Authorization: Bearer {GITHUB_PAT}` from environment variable
- **Auth Levels:**
  - Read operations (list repos, get file, search code) → `AuthLevel.READ_AUTO`
  - Write operations (create issue, create PR, add comment) → `AuthLevel.WRITE_NOTIFY`
  - Destructive operations (delete repo, close PR) → `AuthLevel.DESTRUCTIVE_APPROVAL`
- **Cost:** $0 (GitHub API is free with PAT)
- **Rate Limit:** 5000 requests/hour (authenticated)

### Function Signatures

```python
async def github_list_repos(owner: str) -> list[dict[str, str]]:
    """List repositories for an owner. Auth: READ_AUTO."""

async def github_get_file(owner: str, repo: str, path: str) -> str:
    """Get file contents from a repo. Auth: READ_AUTO."""

async def github_create_issue(owner: str, repo: str, title: str, body: str) -> dict[str, object]:
    """Create an issue. Auth: WRITE_NOTIFY."""

async def github_create_pr(owner: str, repo: str, title: str, head: str, base: str) -> dict[str, object]:
    """Create a pull request. Auth: WRITE_NOTIFY."""

async def github_search_code(query: str) -> list[dict[str, str]]:
    """Search code across GitHub. Auth: READ_AUTO."""
```

### Error Handling

- 401 Unauthorized → log + raise `ConfigurationError` (invalid PAT)
- 403 Rate Limited → log + return rate limit info, suggest backoff
- 404 Not Found → log + return empty result
- Missing `GITHUB_PAT` → raise `ConfigurationError` at import time

## Evidence Requirements

- `docs/setup-evidence/P6/STEP-P6-007/verification.md` — 12-section verification report
- `docs/setup-evidence/P6/STEP-P6-007/auditor-gate.md` — auditor verdict

## Hard Rejection Criteria

- [ ] All expected files exist
- [ ] All forbidden patterns return zero matches
- [ ] All required commands pass (exit 0)
- [ ] Evidence files exist and are non-empty
- [ ] No PAT or tokens in source file — `GITHUB_PAT` from `os.environ` only
- [ ] Three auth levels enforced per operation type
- [ ] `httpx.AsyncClient` used with `base_url` for API
- [ ] Rate limit response headers parsed and logged
- [ ] `structlog` used for all logging
- [ ] Tests use mocked httpx responses (no live API calls)
