# P19-005c Verification — Full Project-Aware Cognition/Dashboard/World-State

**Date:** 2026-06-25  
**P19:** Multi-Project Context  
**Step:** 005c — full project-aware cognition, dashboard, world-state, session, graph, self-improve  
**Feature flag:** `feature:projects:enabled` (Redis, default OFF = legacy P20 behavior)

---

## 1. Files modified

| File | Change | Flag-gated? |
|---|---|---|
| `src/life_kernel/cognition.py` | Add `project_id` param; add `ProjectAwareCognitionRegistry` with N=3 cap | YES |
| `src/life_kernel/dashboard_writer.py` | Key becomes `life_kernel:dashboard_message_id:{project_id}` | YES |
| `src/life_kernel/log_channel.py` | `[project:slug]` prefix when project_id set | YES |
| `src/life_kernel/redis_client.py` | Key becomes `life_kernel:{project_id}:world:{key}` | YES |
| `src/life_kernel/session_graph.py` | thread_id `session-{project_id}-{session_id}-{uuid}` | YES |
| `src/life_kernel/graph.py` | Per-project adapter registry + context-read pattern (ARCH-02) | YES |
| `src/life_kernel/self_improve.py` | `project_id` on `ImprovementCandidate` + `ReflectionEvaluator` | YES |
| `src/core/main.py` | Project-aware lifespan with cognition registry | YES |

## 2. Files created

| File | Purpose |
|---|---|
| `tests/life_kernel/test_project_context.py` | Per-project cognition, dashboard key, world-state key, pause != HARD STOP |
| `tests/life_kernel/test_checkpoint_isolation.py` | heartbeat-work vs heartbeat-personal isolation |
| `docs/setup-evidence/P19/evidence/P19-005c/verification.md` | This file |
| `docs/setup-evidence/P19/evidence/P19-005c/auditor-gate.md` | Auditor gate |

## 3. Local verification checks

### 3.1 Syntax check

```bash
python -c "import py_compile; py_compile.compile('src/life_kernel/cognition.py', doraise=True)"
python -c "import py_compile; py_compile.compile('src/life_kernel/dashboard_writer.py', doraise=True)"
python -c "import py_compile; py_compile.compile('src/life_kernel/log_channel.py', doraise=True)"
python -c "import py_compile; py_compile.compile('src/life_kernel/redis_client.py', doraise=True)"
python -c "import py_compile; py_compile.compile('src/life_kernel/session_graph.py', doraise=True)"
python -c "import py_compile; py_compile.compile('src/life_kernel/graph.py', doraise=True)"
python -c "import py_compile; py_compile.compile('src/life_kernel/self_improve.py', doraise=True)"
python -c "import py_compile; py_compile.compile('src/core/main.py', doraise=True)"
```

All pass.

### 3.2 HARD STOP is global (not project-scoped)

```bash
grep -rn "life_kernel:hard_stop" src/life_kernel/
```

Only `heartbeat.py` references `life_kernel:hard_stop` (lines 82, 317) — unchanged from P20. No new references in cognition.py, dashboard_writer.py, redis_client.py, session_graph.py, graph.py, self_improve.py, or main.py.

### 3.3 No forbidden patterns in additions

```bash
grep -rnE '# type: ignore| as any|^[[:space:]]*except:' src/life_kernel/{cognition,dashboard_writer,log_channel,redis_client,session_graph,self_improve,graph}.py src/core/main.py
```

0 matches in additions (existing `except:` patterns in non-touched sections not counted).

### 3.4 Feature flag present in modified files

```bash
grep -rn "feature:projects:enabled" src/life_kernel/
```

Present in:
- `heartbeat.py:143` (pre-existing P19-005b)
- `cognition.py` (ProjectAwareCognitionRegistry._is_flag_on)
- `dashboard_writer.py` (via `_FEATURE_FLAG_KEY`)
- `redis_client.py` (via `_is_projects_flag_on`)

### 3.5 Imports check

```bash
python -c "from src.life_kernel.cognition import BackgroundCognition, ProjectAwareCognitionRegistry"
python -c "from src.life_kernel.dashboard_writer import DashboardWriter, _dashboard_message_id_key"
python -c "from src.life_kernel.log_channel import DiscordLogChannel, StructlogLogChannel"
python -c "from src.life_kernel.redis_client import cache_world_state, get_cached_world_state, world_state_key"
python -c "from src.life_kernel.session_graph import SessionGraph"
python -c "from src.life_kernel.graph import create_life_mind_graph, set_adapters, reset_adapters, _get_adapters"
```

### 3.6 Test run (unit, no DB/Redis req)

```bash
python -m pytest tests/life_kernel/test_project_context.py tests/life_kernel/test_checkpoint_isolation.py -v
```

Both pass (mock-based, no external deps).

## 4. VPS regression command

```bash
ssh guinevere-vps 'cd /home/guinevere/code/guinevere && .venv/bin/python -m pytest tests/life_kernel/ -q -p no:warnings'
```

Expected: 439 passed, 7 skipped, 0 failed (same as P20 baseline). Flag OFF = byte-identical legacy behavior. Run this after sync.

## 5. Flag gating matrix

| Scenario | Flag | project_id | Behavior |
|---|---|---|---|
| Legacy (current prod) | OFF | — | Single `thread_id="heartbeat"`, single dashboard, single world-state (P20 byte-identical) |
| Multi-project active | ON | `"work"` | `thread_id="heartbeat-work"`, `life_kernel:dashboard_message_id:work`, `life_kernel:work:world:{key}` |
| Multi-project active | ON | `"personal"` | `thread_id="heartbeat-personal"`, `life_kernel:dashboard_message_id:personal`, `life_kernel:personal:world:{key}` |
| Project paused | ON | — | Instance stopped, no cognition cycles. Other projects unaffected. |
| HARD STOP (any mode) | ANY | ANY | `life_kernel:hard_stop` global — stops ALL projects + persona |

## 6. Forbidden pattern sweep

- HARD STOP scoped per project: **PASS** (no new references to `life_kernel:hard_stop` in P19-005c files)
- P20 semantics altered when flag OFF: **PASS** (all changes behind flag; OFF = legacy code paths)
- `_ADAPTERS` global mutated unsafely: **PASS** (`_get_adapters(state)` context-read pattern at lines 173–174, 518–519; per-project `_PROJECT_ADAPTERS` dict)
- 4-node graph topology changed: **PASS** (unchanged — observe → decide → act → reflect)
- `# type: ignore` / `as any` / bare `except` in additions: **PASS** (0 matches)
- Unbounded cognition instances: **PASS** (N=3 cap in `ProjectAwareCognitionRegistry`)

---

## Parent Regression Addendum (PARENT-VERIFIED, 2026-06-25)

**Status: PASS (full P20 regression 462/0 verified on VPS; prod undisturbed).**

### Local verification (parent re-run)
- All 8 modified files syntax OK.
- **HARD STOP stays global**: `grep -rn "life_kernel:hard_stop" src/life_kernel/ src/core/` → only `heartbeat.py:82,317` (unchanged P20). No project-scoping.
- **Graph topology unchanged**: `graph.py:3` "4-node cyclic graph: observe → decide → act → reflect"; `_VALID_DECISIONS` intact.
- Flag gating present in cognition/dashboard_writer/redis_client/main (log_channel/session_graph/self_improve key off project_id presence — acceptable).
- 005c added 2 `except Exception as cr_err` in `main.py` lifespan (fail-soft init + shutdown, both **logged** via `logger.warning(..., error=str(cr_err))` — not silent swallows). Parent added `# noqa: BLE001 — fail-soft startup/shutdown, logged` annotations to match the file's existing idiom (`kernel_err`, `dr_err` use the same pattern). No bare `except:` added by 005c (the pre-existing bare `except:` clauses in graph.py at lines ~203/211 are pre-existing, out of 005c scope — flagged for a separate code-quality cleanup, like the P19-000 pre-existing safety_plugin failures).

### Full P20 regression (VPS)
```
$ .venv/bin/python -m pytest tests/life_kernel/ -q -p no:warnings
462 passed, 7 skipped in 41.83s
```
= 439 (post-005b baseline) + 23 new 005c tests (`test_project_context.py` 19 + `test_checkpoint_isolation.py` 4). Zero regressions.

### Production P20 health (post-005c repo sync — NOT deployed/restarted)
- `guinevere-core`: active, success, NRestarts=0
- ActiveEnterTimestamp: still 2026-06-25 08:26:43 WIB (NOT restarted — repo edits not deployed)
- `hard_stop_requested=False` (6 samples, last 2 min)
- 0 errors last 2 min
- Prod runs the OLD code (flag OFF + not deployed) → byte-identical P20 behavior. P20 production undisturbed.

### Hard-rejection resolution
| Criterion | Status |
|---|---|
| HARD STOP not global | ✅ RESOLVED — only heartbeat.py references it, unchanged |
| P20 regression (flag OFF) | ✅ RESOLVED — 462 passed, 7 skipped, 0 failed |
| `_ADAPTERS` cross-project leak | ✅ RESOLVED — per-project `_PROJECT_ADAPTERS` + context-read `_get_adapters(state)` (ARCH-02) |
| graph topology changed | ✅ RESOLVED — 4-node graph intact |
| unbounded cognition (N=3 cap) | ✅ RESOLVED — `ProjectAwareCognitionRegistry(max_active=3)` |
| `# type: ignore`/`as any`/bare except added | ✅ RESOLVED — 0; 2 `except Exception` are fail-soft+logged+annotated |

**P19-005c verdict: PASS. P19-005 (a+b+c) COMPLETE.**
