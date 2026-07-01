# P19-005c Auditor Gate — Full Project-Aware Cognition

**Date:** 2026-06-25  
**Auditor:** (operator / CI)  
**Feature flag:** `feature:projects:enabled` (Redis, default OFF)

---

## Gate criteria

| ID | Criterion | Status | Evidence |
|---|---|---|---|
| C1 | HARD STOP remains global key `life_kernel:hard_stop` | PASS | `grep -rn "life_kernel:hard_stop" src/life_kernel/` shows only `heartbeat.py:82,317` (P20 unchanged) |
| C2 | P20 regression: flag OFF = byte-identical | PASS | All changes behind `feature:projects:enabled` flag; OFF = legacy code paths |
| C3 | `ProjectAwareCognitionRegistry` bounds to N=3 | PASS | `max_active=3` in constructor; `get_or_create` returns `None` when full |
| C4 | Dashboard writer key is project-scoped | PASS | `_dashboard_message_id_key("work")` returns `life_kernel:dashboard_message_id:work`; no project_id = global |
| C5 | World-state key is project-scoped | PASS | `world_state_key(key, project_id="work")` returns `life_kernel:work:world:{key}` with flag ON |
| C6 | Session thread_id includes project_id | PASS | `SessionGraph("s-1", project_id="w")` → `thread_id.startswith("session-w-s-1-")` |
| C7 | Per-project adapter registry (ARCH-02 fix) | PASS | `_PROJECT_ADAPTERS` dict + `_get_adapters(state)` context-read pattern |
| C8 | 4-node graph topology unchanged | PASS | observe → decide → act/reflect/idle → END (unchanged) |
| C9 | No `# type: ignore` / `as any` / bare `except` in additions | PASS | `grep` returns 0 in P19-005c additions |
| C10 | Project pause != HARD STOP | PASS | `pause_project()` stops one instance; other projects + HARD STOP unaffected |
| C11 | Forbidden patterns verified | PASS | See verification.md §6 |
| C12 | Tests exist & pass | PASS | `test_project_context.py` (mock-based), `test_checkpoint_isolation.py` |

## How to verify in production

### Pre-deploy (flag OFF, legacy P20)

```bash
redis-cli -p 6380 -a "$REDIS_PASSWORD" GET feature:projects:enabled
# → (nil) or "false"  (flag OFF)

# Verify P20 regression:
cd /home/guinevere/code/guinevere && \
  .venv/bin/python -m pytest tests/life_kernel/ -q -p no:warnings
# → 439 passed, 7 skipped, 0 failed
```

### Post-deploy (flag OFF, same P20 behavior)

```bash
systemctl restart guinevere-core
# Verify kernel starts & heartbeats healthy via journalctl
# life_kernel:dashboard_message_id still global (verify via redis-cli)
```

### When ready to enable multi-project (operator decision)

```bash
redis-cli -p 6380 -a "$REDIS_PASSWORD" SET feature:projects:enabled "true"
systemctl restart guinevere-core

# Verify per-project behavior:
redis-cli -p 6380 -a "$REDIS_PASSWORD" --scan --pattern 'life_kernel:*'
# → Expected: life_kernel:dashboard_message_id:{project_id} keys
# → Expected: life_kernel:{project_id}:world:* keys
# → NOT expected: life_kernel:hard_stop:* (must stay global)
```

### Rollback

```bash
redis-cli -p 6380 -a "$REDIS_PASSWORD" SET feature:projects:enabled "false"
systemctl restart guinevere-core
# → Restores legacy P20 single-project behavior
```

---

## Decision

**PASS** — All 12 criteria met. Ready for P20 regression on VPS.
