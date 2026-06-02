# Scaffold: STEP-P6-012 — websearch (Hybrid Brave→Exa)

## Expected Files

- `src/mcp/tools/websearch.py` — Hybrid web search (Brave primary, Exa fallback)
- `tests/mcp/test_websearch.py` — Unit tests for hybrid fallback logic

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
- Direct API calls (must import from `brave_search` and `exa_search` modules)

## Required Commands

| Command | Expected Exit Code | Notes |
|---------|-------------------|-------|
| `python -m pytest tests/mcp/test_websearch.py -v` | 0 | All tests pass, including fallback |
| `python -m ruff check src/mcp/tools/websearch.py` | 0 | No lint errors |
| `python -m mypy src/mcp/tools/websearch.py` | 0 | No type errors |

## Implementation Details

### Key Design

- **Primary:** Brave Search (P6-002) — fast, cheap ($0.01/search)
- **Fallback:** Exa Search (P6-004) — semantic, $0.007/request, $5/day cap
- **Fallback Triggers:** Brave returns empty results, Brave raises error, or Brave rate-limited
- **Auth Level:** `AuthLevel.READ_AUTO`
- **Cost:** Variable — Brave $0.01/search + Exa $0.007/search (only on fallback)
- **Dependencies:** P6-002 (brave_search) + P6-004 (exa_search) must both be implemented

### Function Signature

```python
async def websearch(
    query: str,
    count: int = 5,
    prefer: str = "brave",
) -> dict[str, object]:
    """Hybrid web search: tries Brave first, falls back to Exa.
    
    Returns dict with 'results', 'source' ('brave' or 'exa'), 'fallback_used'.
    """
```

### Fallback Logic

```python
async def websearch(query: str, count: int = 5, prefer: str = "brave") -> dict:
    # Try primary
    try:
        if prefer == "brave":
            results = await brave_search(query, count)
            if results:
                return {"results": results, "source": "brave", "fallback_used": False}
    except (BudgetExceeded, Exception) as e:
        logger.warning("websearch.primary_failed", error=str(e), query=query)
    
    # Fallback
    try:
        results = await exa_search(query, num_results=count)
        return {"results": results, "source": "exa", "fallback_used": True}
    except BudgetExceeded:
        logger.error("websearch.both_budget_exceeded", query=query)
        return {"results": [], "source": "none", "fallback_used": True, "error": "budget_exceeded"}
```

### Error Handling

- Both services fail → return empty results with error context
- Both budgets exceeded → return empty results with "budget_exceeded" error
- Primary returns empty → trigger fallback silently

## Evidence Requirements

- `docs/setup-evidence/P6/STEP-P6-012/verification.md` — 12-section verification report
- `docs/setup-evidence/P6/STEP-P6-012/auditor-gate.md` — auditor verdict

## Hard Rejection Criteria

- [ ] All expected files exist
- [ ] All forbidden patterns return zero matches
- [ ] All required commands pass (exit 0)
- [ ] Evidence files exist and are non-empty
- [ ] No API keys in source file
- [ ] Auth level `READ_AUTO` enforced
- [ ] Brave is primary, Exa is fallback
- [ ] Fallback triggers on: empty results, error, rate limit, budget exceeded
- [ ] `BudgetExceeded` from Exa handled gracefully (returns empty, not crash)
- [ ] Return dict includes `source` and `fallback_used` fields
- [ ] Tests verify: primary success, primary fail → fallback, both fail
- [ ] `structlog` used for all logging
