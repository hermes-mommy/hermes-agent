# Scaffold: STEP-P6-020 — Cost Tracking Per Tool

## Expected Files

- `src/mcp/cost.py` — Per-tool cost tracking in Redis DB5
- `tests/mcp/test_cost.py` — Unit tests with mocked Redis

## Forbidden Patterns

- `as any`
- `@ts-ignore`
- `# type: ignore`
- `cast(`
- `except Exception:` (empty/swallowed)
- `except:` (bare)
- `print(` (use structlog)
- `import logging` (use structlog)
- Hardcoded Redis passwords

## Required Commands

| Command | Expected Exit Code | Notes |
|---------|-------------------|-------|
| `python -m pytest tests/mcp/test_cost.py -v` | 0 | All tests pass |
| `python -m ruff check src/mcp/cost.py` | 0 | No lint errors |
| `python -m mypy src/mcp/cost.py` | 0 | No type errors |

## Implementation Details

### Key Design

- **Redis DB:** 5 (same as existing `CostTracker` and `LoopCostTracker`)
- **Key Format:** `tool:cost:{tool_name}:YYYY-MM-DD`
- **Value:** Microdollars (INCRBYFLOAT for atomic increment)
- **Daily Expiry:** `EXPIREAT` set to next day 00:00:00 UTC
- **Port:** 6380
- **Pattern:** Follow existing `src/core/services/cost_tracker.py` and `src/loops/cost.py`

### Cost Per Tool

| Tool | Cost Per Call | Notes |
|------|--------------|-------|
| brave_search | $0.01 | Per search |
| context7 | $0.00 | Free tier |
| exa | $0.007 | Per search |
| fetch | $0.00 | No API cost |
| filesystem | $0.00 | Local operation |
| github | $0.00 | Free with PAT |
| grep_app | $0.00 | Public API |
| obscura_cdp | $0.00 | Local operation |
| sequential_thinking | $0.00 | LLM cost tracked separately |
| time | $0.00 | Local operation |
| websearch | Variable | Brave + Exa on fallback |
| git | $0.00 | Local operation |
| postgres | $0.00 | Local operation |
| redis | $0.00 | Local operation |
| shell | $0.00 | Local operation |
| docker | $0.00 | Local operation |

### Function Signatures

```python
class ToolCostTracker:
    """Per-tool cost tracking in Redis DB5."""

    def __init__(self, host: str = "localhost", port: int = 6380, db: int = 5) -> None:
        ...

    async def record_tool_cost(self, tool_name: str, cost_usd: float) -> float:
        """Record cost for a tool call. Returns daily total for that tool."""

    async def get_tool_daily_cost(self, tool_name: str) -> float:
        """Get current daily cost for a tool."""

    async def get_all_daily_costs(self) -> dict[str, float]:
        """Get daily costs for all tools today."""

    async def get_tool_monthly_cost(self, tool_name: str) -> float:
        """Get monthly total for a tool."""
```

### Redis Key Schema

```
tool:cost:brave_search:2026-06-02    → 0.15  (microdollars)
tool:cost:exa:2026-06-02             → 0.035
tool:cost:websearch:2026-06-02       → 0.12
tool:cost:total:2026-06-02           → 0.305  (aggregate)
```

### Integration Point

Each tool's implementation calls `ToolCostTracker.record_tool_cost()` after a successful API call. This is done via the `@require_approval` decorator or an explicit call within each tool function.

## Evidence Requirements

- `docs/setup-evidence/P6/STEP-P6-020/verification.md` — 12-section verification report
- `docs/setup-evidence/P6/STEP-P6-020/auditor-gate.md` — auditor verdict

## Hard Rejection Criteria

- [ ] All expected files exist
- [ ] All forbidden patterns return zero matches
- [ ] All required commands pass (exit 0)
- [ ] Evidence files exist and are non-empty
- [ ] No hardcoded Redis passwords
- [ ] Redis DB5 used (not other DBs)
- [ ] Key format `tool:cost:{name}:YYYY-MM-DD` verified in tests
- [ ] INCRBYFLOAT used for atomic increment
- [ ] EXPIREAT set for daily key rotation
- [ ] Port 6380 used in default config
- [ ] `structlog` used for all logging
- [ ] Follows existing `CostTracker` pattern from `src/core/services/cost_tracker.py`
- [ ] Tests verify per-tool cost recording and retrieval
