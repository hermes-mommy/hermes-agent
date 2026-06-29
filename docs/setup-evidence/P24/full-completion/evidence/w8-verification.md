# W8 Sub-agents Verification

**Wave**: W8 (M5 Sub-agents)
**Date**: 2026-06-29

## Files Created
- `guinevere/iteration_budget.py` — MaxDepthReached exception, global threading.Semaphore(10), spawn rate limiter (30/hour), SubagentSlot context manager
- `tests/p24/test_subagents.py` — 18 tests covering constants, MaxDepthReached, semaphore, rate limit, hash chain, DELEGATE_BLOCKED_TOOLS

## Files Modified
- `tools/delegate_tool.py` — surgical edits only:
  - L140: `_DEFAULT_MAX_CONCURRENT_CHILDREN = 10` (was 3)
  - L141: `MAX_DEPTH = 5` (was 1)
  - L145: `_MAX_SPAWN_DEPTH_CAP = 5` (was 3)
  - L401: docstring "clamped to [1, 5]" (was [1, 3])
  - L41-48: import MaxDepthReached, acquire_subagent_slot, release_subagent_slot, SubagentSlot, check_spawn_rate, record_spawn from guinevere.iteration_budget
  - L1969: raise MaxDepthReached(...) instead of JSON error return
  - L1971-1976: spawn rate limit check (30/hour)
  - L1340-1355: semaphore acquire before child execution, release in finally
  - L1490-1498: hash-chain field (SHA-256 of parent's last audit row) in _register_subagent call
  - DELEGATE_BLOCKED_TOOLS UNCHANGED (C4)

## Required Command Output

### Constants 10/5/5
```
140:_DEFAULT_MAX_CONCURRENT_CHILDREN = 10
141:MAX_DEPTH = 5
145:_MAX_SPAWN_DEPTH_CAP = 5
```

### MaxDepthReached import
```
MaxDepthReached OK
```

### Global semaphore
```
cap: 10
```

### delegate_tool imports
```
delegate_tool imports OK
```

### Tests
```
18 passed in 3.86s
```

### DELEGATE_BLOCKED_TOOLS unchanged (C4)
```
DELEGATE_BLOCKED_TOOLS = frozenset(
    ["delegate_task", "clarify", "memory", "send_message", "execute_code"]
)
```

## Critical Corrections Followed
- C4: DELEGATE_BLOCKED_TOOLS unchanged — delegate_task still in frozenset
- C5: threading.Semaphore (not asyncio.Semaphore) — ThreadPoolExecutor based
- C6: MaxDepthReached exception created, raised at depth check, backward-compat JSON via caller
- C7: guinevere/iteration_budget.py is separate from agent/iteration_budget.py (different concepts)
