# W12 — M8 Unified Tool Registry: Verification Evidence

**Date:** 2026-06-29
**Verdict:** PASS

---

## Files Created

| # | File | Lines | Purpose |
|---|------|-------|---------|
| 1 | `guinevere/tools/__init__.py` | 20 | Re-exports ToolBackend, ToolRegistry, backends, wire |
| 2 | `guinevere/tools/tool_backend.py` | 296 | ActionTier enum (L1-L3), Action dataclass, AuditRecord, hash-chain audit, _DurableQueue, ToolBackend ABC, ToolRegistry singleton, discover_backends() |
| 3 | `guinevere/tools/registry.py` | 46 | register_all(), wire(agent) for Group D agent_init append |
| 4 | `guinevere/tools/backends/__init__.py` | 23 | Re-exports all 9 backends |
| 5 | `guinevere/tools/backends/browser.py` | 99 | 11 actions (7 L1, 4 L2) |
| 6 | `guinevere/tools/backends/github.py` | 147 | 19 actions (10 L1, 7 L2, 2 L3) |
| 7 | `guinevere/tools/backends/filesystem.py` | 90 | 9 actions (4 L1, 4 L2, 1 L3) |
| 8 | `guinevere/tools/backends/vps.py` | 123 | 14 actions (6 L1, 7 L2, 1 L3) |
| 9 | `guinevere/tools/backends/email.py` | 100 | 10 actions (3 L1, 7 L2) |
| 10 | `guinevere/tools/backends/desktop.py` | 78 | 6 actions (1 L1, 4 L2, 1 L3) |
| 11 | `guinevere/tools/backends/freelance.py` | 91 | 8 actions (2 L1, 6 L2) |
| 12 | `guinevere/tools/backends/social.py` | 113 | 11 actions (2 L1, 8 L2, 1 L3) |
| 13 | `guinevere/tools/backends/memory.py` | 217 | 30 actions (12 L1, 12 L2, 6 L3) |
| 14 | `tests/p24/test_tool_registry.py` | 384 | 34 tests |

**Total actions: 118** across 9 backends.

---

## Verification Commands

### 1. Import check
```
$ python -c "from guinevere.tools import ToolBackend, ToolRegistry; print('OK')"
OK
```

### 2. 9 backends discovered
```
$ python -c "from guinevere.tools.registry import discover_backends; b=discover_backends(); print('backends:', len(b), sorted([x.name for x in b]))"
backends: 9 ['browser', 'desktop', 'email', 'filesystem', 'freelance', 'github', 'memory', 'social', 'vps']
```

### 3. L1-L3 tiers (NO L4)
```
$ python -c "from guinevere.tools.tool_backend import ActionTier; print('tiers:', [t.name for t in ActionTier])"
tiers: ['L1_READ', 'L2_WRITE', 'L3_DESTRUCTIVE']
```

### 4. Tests pass
```
$ pytest tests/p24/test_tool_registry.py -q
34 passed in 106.62s
```

### 5. No forbidden patterns
```
$ grep -rn 'consent_gate\|L4_FORBIDDEN\|PermissionTier.L4' guinevere/tools/
(exit 1 — 0 matches)
```

### 6. Package import
```
$ python -c "import guinevere.tools; print('imports OK')"
imports OK
```

---

## Action Count Summary

| Backend | Actions | L1 | L2 | L3 |
|---------|---------|----|----|-----|
| browser | 11 | 7 | 4 | 0 |
| github | 19 | 10 | 7 | 2 |
| filesystem | 9 | 4 | 4 | 1 |
| vps | 14 | 6 | 7 | 1 |
| email | 10 | 3 | 7 | 0 |
| desktop | 6 | 1 | 4 | 1 |
| freelance | 8 | 2 | 6 | 0 |
| social | 11 | 2 | 8 | 1 |
| memory | 30 | 12 | 12 | 6 |
| **TOTAL** | **118** | **47** | **59** | **12** |

---

## Design Notes

- **ABC**: `ToolBackend` ABC with `name`, `actions()`, `dispatch()`, `is_available()`, `find_action()`.
- **ActionTier**: Enum with L1_READ, L2_WRITE, L3_DESTRUCTIVE. L4 deleted per ADR-062.
- **UUID v7 + SHA-256 hash-chain**: Every dispatch produces an AuditRecord with UUID v7 action_id and SHA-256 hash chained to previous dispatch.
- **Durable queue**: PG + Redis DB6, fail-soft D2 (no crash when neither available).
- **wire(agent)**: Fail-soft Group D wire function; parent appends to agent_init.py.
- **No consent_gate**: Zero references to consent_gate, L4_FORBIDDEN, or PermissionTier.L4 in guinevere/tools/.
- **No bare except**: All exception handlers use specific exception types or `Exception`.
- **No # type: ignore**: No bare type: ignore comments in source files.
