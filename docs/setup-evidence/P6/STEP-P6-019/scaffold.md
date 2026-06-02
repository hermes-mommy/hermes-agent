# Scaffold: STEP-P6-019 — Tool Selection Decision Matrix

## Expected Files

- `src/mcp/tool_selector.py` — Decision matrix for selecting optimal tool
- `tests/mcp/test_tool_selector.py` — Unit tests for routing decisions

## Forbidden Patterns

- `as any`
- `@ts-ignore`
- `# type: ignore`
- `cast(`
- `except Exception:` (empty/swallowed)
- `except:` (bare)
- `print(` (use structlog)
- `import logging` (use structlog)

## Required Commands

| Command | Expected Exit Code | Notes |
|---------|-------------------|-------|
| `python -m pytest tests/mcp/test_tool_selector.py -v` | 0 | All routing tests pass |
| `python -m ruff check src/mcp/tool_selector.py` | 0 | No lint errors |
| `python -m mypy src/mcp/tool_selector.py` | 0 | No type errors |

## Implementation Details

### Key Design

- **Purpose:** When multiple tools overlap, select the optimal one based on task type, cost, auth level, and availability
- **Scoring:** Priority score = (relevance × 0.4) + (cost_efficiency × 0.3) + (auth_ease × 0.2) + (availability × 0.1)

### Overlap Scenarios

| Task | Candidates | Winner | Rationale |
|------|-----------|--------|-----------|
| Web search (general) | brave_search, exa, websearch | websearch | Hybrid fallback built-in |
| Web search (semantic) | exa, websearch | exa | Better for semantic queries |
| Code search | grep_app, github (code search) | grep_app | Purpose-built for code |
| Library docs | context7, fetch | context7 | Structured doc lookup |
| Page content | fetch, obscura_cdp | fetch | Lighter for simple fetches |
| File read | filesystem, shell (cat) | filesystem | Purpose-built, safer |
| DB query | postgres, shell (psql) | postgres | Typed, parameterized, safer |
| Git operations | git, shell (git) | git | Auth-level granularity |

### Data Model

```python
@dataclass(frozen=True)
class ToolOption:
    name: str
    relevance: float  # 0.0–1.0
    cost_efficiency: float  # 0.0–1.0
    auth_ease: float  # 0.0–1.0 (READ_AUTO=1.0, FORBIDDEN=0.0)
    available: bool  # service reachable

@dataclass(frozen=True)
class ToolRecommendation:
    tool_name: str
    score: float
    alternatives: tuple[ToolOption, ...]
    reason: str
```

### Function Signatures

```python
async def select_tool(
    task_type: str,
    query: str = "",
    constraints: dict[str, object] | None = None,
) -> ToolRecommendation:
    """Select the optimal tool for a given task."""

def get_tool_matrix() -> dict[str, list[str]]:
    """Return the full tool selection decision matrix."""
```

### Error Handling

- No suitable tool found → raise `NoToolAvailableError` with suggestions
- All candidates unavailable → raise `AllToolsUnavailableError`

## Evidence Requirements

- `docs/setup-evidence/P6/STEP-P6-019/verification.md` — 12-section verification report
- `docs/setup-evidence/P6/STEP-P6-019/auditor-gate.md` — auditor verdict

## Hard Rejection Criteria

- [ ] All expected files exist
- [ ] All forbidden patterns return zero matches
- [ ] All required commands pass (exit 0)
- [ ] Evidence files exist and are non-empty
- [ ] All 8 overlap scenarios tested with correct winner
- [ ] Frozen dataclass used for ToolOption and ToolRecommendation
- [ ] Priority scoring formula implemented as specified
- [ ] `structlog` used for all logging
- [ ] Tests verify websearch preferred over brave_search for general search
- [ ] Tests verify grep_app preferred over github for code search
