# P5 Fix Execution Report: F-02, F-03, F-06

Generated: 2026-06-09  
Executor: subagent  
Project: /home/guinevere/code/guinevere

---

## F-02: Enable Systemd Services

### Action Attempted

```
sudo systemctl enable guinevere-loops guinevere-scheduler
```

### Result: SKIP — requires root SSH

```
sudo: The "no new privileges" flag is set, which prevents sudo from running as root.
sudo: If sudo is running in a container, you may need to adjust the container
      configuration to disable the flag.
```

### Pre-fix state

```
systemctl is-enabled guinevere-loops guinevere-scheduler
→ disabled
→ disabled
```

### Resolution

**Status: requires root SSH**  
The `NoNewPrivileges` flag is active on this host (container/systemd sandbox), which prevents `sudo` from escalating privileges. The service unit files exist and are recognized by systemd but cannot be enabled from this session.

**To fix manually (via root SSH):**
```bash
ssh root@<host>
systemctl enable guinevere-loops guinevere-scheduler
systemctl is-enabled guinevere-loops guinevere-scheduler
# Expected: enabled / enabled
```

---

## F-03: Fix Async E2E Test

### Problem Analysis

File: `tests/test_e2e_loop.py`

- `test_full_loop_cycle()` is an `async def` function
- No `@pytest.mark.asyncio` decorator present
- `pyproject.toml [tool.pytest.ini_options]` was missing `asyncio_mode = "auto"`
- Without `asyncio_mode = "auto"`, pytest-asyncio does not auto-detect async test functions

### Fix Applied

File modified: `pyproject.toml`

```diff
 [tool.pytest.ini_options]
 testpaths = ["tests"]
 pythonpath = ["src"]
+asyncio_mode = "auto"
```

### Verification

```
$ .venv/bin/python3 -m pytest tests/test_e2e_loop.py -q --tb=short 2>&1 | tail -10
.                                                                        [100%]
1 passed in 4.07s
```

**Status: PASS** ✓

---

## F-06: Fix cost.py float() ValueError

### Problem Analysis

File: `src/loops/cost.py`

All `float()` calls reading Redis string values were wrapped only in `try/except RedisError` blocks. If Redis returns a corrupt or non-numeric string, `float()` raises `ValueError` — which is not a subclass of `RedisError` and would propagate uncaught, potentially crashing callers.

### Affected Locations

| Method | Line (original) | Expression |
|---|---|---|
| `record_loop_cost` | 107 | `float(self.redis.get(loop_key) or 0)` |
| `get_loop_cost` | 156 | `float(total_cost_str) if total_cost_str else 0.0` |
| `get_loop_cost` | 171 | `float(model_cost_str) if model_cost_str else 0.0` |
| `get_all_loop_costs` | 221 | `float(cost_str) if cost_str else 0.0` |

### Fix Applied

Each `float()` call wrapped in its own `try/except ValueError` block that:
- Logs a `warning` with `loop_id`, method context, and `raw_value` for observability
- Returns `0.0` as safe default (no crash, no data loss)

Example pattern applied:

```python
try:
    total_cost = float(total_cost_str) if total_cost_str else 0.0
except ValueError:
    logger.warning(
        "loop_cost.invalid_total_cost_float",
        loop_id=loop_id,
        raw_value=total_cost_str,
    )
    total_cost = 0.0
```

Warning event names introduced:
- `loop_cost.invalid_float` (in `record_loop_cost`)
- `loop_cost.invalid_total_cost_float` (in `get_loop_cost` — total)
- `loop_cost.invalid_model_cost_float` (in `get_loop_cost` — per-model)
- `loop_cost.invalid_all_costs_float` (in `get_all_loop_costs`)

### Verification

```
$ .venv/bin/python3 -c "from src.loops.cost import *; print('OK')"
OK
```

**Status: PASS** ✓

---

## Summary

| Fix | Status | Notes |
|---|---|---|
| F-02 | SKIP — requires root SSH | `NoNewPrivileges` prevents sudo; services recognized but disabled; fix via `ssh root@<host> systemctl enable ...` |
| F-03 | PASS | Added `asyncio_mode = "auto"` to `[tool.pytest.ini_options]`; `test_full_loop_cycle` passes (1 passed in ~4s) |
| F-06 | PASS | Wrapped all 4 `float()` Redis reads with `try/except ValueError`; import and syntax verified OK |
