# Scaffold: STEP-P6-021 — Budget Enforcement Test

## Expected Files

- `src/mcp/budget.py` — Budget enforcement: daily caps, monthly alerts, fallback logic
- `tests/mcp/test_budget.py` — Comprehensive budget enforcement tests

## Forbidden Patterns

- `as any`
- `@ts-ignore`
- `# type: ignore`
- `cast(`
- `except Exception:` (empty/swallowed)
- `except:` (bare)
- `print(` (use structlog)
- `import logging` (use structlog)
- Hardcoded API keys

## Required Commands

| Command | Expected Exit Code | Notes |
|---------|-------------------|-------|
| `python -m pytest tests/mcp/test_budget.py -v` | 0 | All budget tests pass |
| `python -m ruff check src/mcp/budget.py` | 0 | No lint errors |
| `python -m mypy src/mcp/budget.py` | 0 | No type errors |

## Implementation Details

### Key Design

- **Daily Caps:**
  - Exa: $5/day (hard cap)
  - Brave: $3/day (soft cap, log warning at 80%)
  - All tools: $10/day (emergency hard cap)
- **Monthly Alerts:**
  - $3/month → WARNING alert via Discord
  - $15/month → CRITICAL alert via Discord
  - $25/month → HARD_STOP alert (near $30 cap)
  - $30/month → All paid API calls blocked
- **Fallback Logic:**
  - Exa cap reached → route to Brave via `websearch` hybrid
  - Brave cap reached → log + throttle (no fallback available)
  - Monthly cap reached → all paid tools return `BudgetExceeded`

### Data Model

```python
@dataclass(frozen=True)
class BudgetConfig:
    exa_daily_cap: float = 5.0
    brave_daily_cap: float = 3.0
    global_daily_cap: float = 10.0
    monthly_warning: float = 3.0
    monthly_critical: float = 15.0
    monthly_hard_stop: float = 25.0
    monthly_absolute_cap: float = 30.0

@dataclass(frozen=True)
class BudgetStatus:
    tool: str
    daily_spent: float
    daily_cap: float
    monthly_spent: float
    alert_level: str  # "NORMAL", "WARNING", "CRITICAL", "HARD_STOP"
    fallback_active: bool
```

### Function Signatures

```python
class BudgetEnforcer:
    """Budget enforcement for MCP tools."""

    def __init__(self, config: BudgetConfig | None = None) -> None:
        ...

    async def check_budget(self, tool_name: str) -> BudgetStatus:
        """Check budget status for a tool. Raises BudgetExceeded if cap reached."""

    async def get_fallback_tool(self, tool_name: str) -> str | None:
        """Return fallback tool name if primary is over budget, else None."""

    async def get_monthly_status(self) -> dict[str, BudgetStatus]:
        """Get budget status for all tools this month."""

    async def record_and_check(self, tool_name: str, cost: float) -> BudgetStatus:
        """Record cost and immediately check if budget is breached."""
```

### Test Scenarios

1. **Exa $5 cap triggers Brave fallback:**
   - Set Redis `tool:cost:exa:today` to 4.99
   - Call `check_budget("exa")` with additional $0.01 → should allow
   - Set Redis to 5.00
   - Call `check_budget("exa")` → should raise `BudgetExceeded`
   - Call `get_fallback_tool("exa")` → should return `"brave_search"`

2. **Monthly $30 cap blocks all paid tools:**
   - Set Redis `cost:current_month` to 30.0
   - Call `check_budget("brave_search")` → should raise `BudgetExceeded`

3. **Monthly $3 warning triggers Discord alert:**
   - Set Redis `cost:current_month` to 3.1
   - Call `get_monthly_status()` → alert_level should be "WARNING"

4. **Global $10/day emergency cap:**
   - Set total daily spend to 10.0
   - All tools raise `BudgetExceeded`

## Evidence Requirements

- `docs/setup-evidence/P6/STEP-P6-021/verification.md` — 12-section verification report
- `docs/setup-evidence/P6/STEP-P6-021/auditor-gate.md` — auditor verdict

## Hard Rejection Criteria

- [ ] All expected files exist
- [ ] All forbidden patterns return zero matches
- [ ] All required commands pass (exit 0)
- [ ] Evidence files exist and are non-empty
- [ ] No API keys in source file
- [ ] $5/day Exa cap triggers Brave fallback (tested)
- [ ] $30/month cap blocks all paid tools (tested)
- [ ] $3/month warning triggers Discord alert (tested, mocked)
- [ ] Frozen dataclass used for BudgetConfig and BudgetStatus
- [ ] `BudgetExceeded` exception raised at cap breach
- [ ] `get_fallback_tool("exa")` returns `"brave_search"`
- [ ] `structlog` used for all logging
- [ ] All 4 test scenarios pass
- [ ] Integration with `ToolCostTracker` from P6-020 verified
