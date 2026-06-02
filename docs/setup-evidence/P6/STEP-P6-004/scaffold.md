# Scaffold: STEP-P6-004 — exa

## Expected Files

- `src/mcp/tools/exa_search.py` — Exa AI search MCP tool with $5/day cap
- `tests/mcp/test_exa_search.py` — Unit tests with mocked httpx + Redis

## Forbidden Patterns

- `as any`
- `@ts-ignore`
- `# type: ignore`
- `cast(`
- `except Exception:` (empty/swallowed)
- `except:` (bare)
- Hardcoded API keys (must use `os.environ["EXA_API_KEY"]` or SOPS decryption)
- `print(` (use structlog)
- `import logging` (use structlog)
- `requests.` (use httpx)

## Required Commands

| Command | Expected Exit Code | Notes |
|---------|-------------------|-------|
| `python -m pytest tests/mcp/test_exa_search.py -v` | 0 | All tests pass, including cap enforcement |
| `python -m ruff check src/mcp/tools/exa_search.py` | 0 | No lint errors |
| `python -m mypy src/mcp/tools/exa_search.py` | 0 | No type errors |

## Implementation Details

### Key Design

- **HTTP Client:** `httpx.AsyncClient` with timeout=10s
- **API Endpoint:** `https://api.exa.ai/search` (POST)
- **Auth Header:** `x-api-key` from environment variable `EXA_API_KEY`
- **Auth Level:** `AuthLevel.READ_AUTO`
- **Cost:** $0.007/request
- **Daily Cap:** $5/day enforced via Redis DB5
- **Redis Key:** `tool:cost:exa:YYYY-MM-DD` — INCRBYFLOAT microdollars
- **Cap Check:** Before API call, check Redis counter; if >= $5, raise `BudgetExceeded`
- **Cost Model (FinOps v1.1):**
  - Daily burst cap: $5/day
  - Monthly throttle trigger: $3/month
  - Average monthly spend: ~$1/month

### Function Signature

```python
async def exa_search(query: str, num_results: int = 10) -> list[dict[str, str]]:
    """AI-powered semantic search via Exa. $5/day cap enforced."""
```

### Budget Exceeded Exception

```python
class BudgetExceeded(Exception):
    """Raised when daily spending cap is reached."""
```

### Error Handling

- Budget exceeded → raise `BudgetExceeded` with current spend and cap
- `httpx.HTTPStatusError` (429) → log + return empty list
- Missing `EXA_API_KEY` → raise `ConfigurationError` at import time

## Evidence Requirements

- `docs/setup-evidence/P6/STEP-P6-004/verification.md` — 12-section verification report
- `docs/setup-evidence/P6/STEP-P6-004/auditor-gate.md` — auditor verdict

## Hard Rejection Criteria

- [ ] All expected files exist
- [ ] All forbidden patterns return zero matches
- [ ] All required commands pass (exit 0)
- [ ] Evidence files exist and are non-empty
- [ ] No API keys in source file — `EXA_API_KEY` from `os.environ` only
- [ ] Auth level `READ_AUTO` enforced
- [ ] `$5/day` cap check occurs BEFORE API call (not after)
- [ ] Redis DB5 key format: `tool:cost:exa:YYYY-MM-DD`
- [ ] INCRBYFLOAT used for cost recording (microdollars)
- [ ] `BudgetExceeded` exception raised when cap breached
- [ ] Tests verify cap enforcement with mocked Redis
- [ ] `structlog` used for all logging
