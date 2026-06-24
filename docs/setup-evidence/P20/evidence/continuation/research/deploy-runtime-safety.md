# P20 Living Autonomy Kernel — Deploy / Runtime Safety Research

**Role:** deployment / runtime safety researcher  
**Date:** 2026-06-24  
**VPS:** guinevere-vps (Tailscale 100.94.104.22)  
**Target service:** `guinevere-core.service`  
**Output file:** `docs/setup-evidence/P20/evidence/continuation/research/deploy-runtime-safety.md`

---

## 1. Executive Summary

The P20 Living Autonomy Kernel is **production-deployed and runtime-stable**. All five pre-production stabilization bugs (port 9191 crash loop, guardian `AttributeError`, Postgres checkpointer async-context-manager misuse, DSN mismatch, and `GraphRecursionError`) are fixed and verified on the VPS. The service has been running with two uvicorn workers, PostgreSQL checkpointing, Redis-backed HARD STOP, and Discord-visible dashboard/log publishing. The 10s/30s/5m/1h heartbeat handlers remain intentional stubs and are not safety-critical.

This report identifies the **remaining functional placeholders** that block full LK-010+ autonomy, confirms the current deploy and rollback path, and provides a concrete, safe implementation plan for the continuation phase.

---

## 2. Current State Evidence (with file:line citations)

### 2.1 Heartbeat service: safety path is live, stubs are documented

`src/life_kernel/heartbeat.py:254-357` implements the 1s safety heartbeat with live Redis HARD STOP detection, stale-checkpoint recovery, Discord dashboard HARD STOP publish, lifecycle log write, and service stop.

```python
# heartbeat.py:274
hard_stop_value = await self.redis_client.get(hard_stop_key)
...
live_hard_stop = bool(hard_stop_value)
if live_hard_stop:
    ...
    await self.stop()
```

The 10s, 30s, 5m, and 1h handlers are explicit placeholders:

- `_heartbeat_10s` (`heartbeat.py:373-398`): only logs `heartbeat_10s_graph_health_check`; comment says "Placeholder for future stuck detection logic."
- `_heartbeat_30s` (`heartbeat.py:400-419`): only logs `heartbeat_30s_awareness_refresh`; comment says "Placeholder for future sensor integration."
- `_heartbeat_5m` (`heartbeat.py:530-549`): only logs `heartbeat_5m_deep_scan`; comment says "Placeholder for future domain mind scanning."
- `_heartbeat_1h` (`heartbeat.py:551-571`): only logs `heartbeat_1h_reflection`; comment says "Placeholder for future reflection logic."

These stubs are **accepted non-blocking placeholders** per the authoritative context: the operator-approved continuation pass is to wire real substrates (P16 KG, P18 memory, sensors, domain minds) behind these hooks, not to remove the stubs.

### 2.2 Graph: terminates safely, recursion limit set

`src/life_kernel/graph.py:697-749` defines the life-mind graph. The previously infinite cycle was fixed by routing `reflect → END` and `idle → END`:

```python
builder.add_edge("reflect", END)
builder.add_edge("idle", END)
```

`recursion_limit=25` is set at every `graph.ainvoke` call site:

- `src/life_kernel/heartbeat.py:303`
- `src/life_kernel/heartbeat.py:340`
- `src/life_kernel/heartbeat.py:466`
- `src/life_kernel/cognition.py:248`

With the graph now completing exactly one cycle per invoke (observe → decide → act/reflect/idle → END), 25 steps is far above the observed path length and acts as a fail-fast guard rather than a practical limit.

### 2.3 Checkpointer: async context manager pattern is fixed

`src/life_kernel/checkpoint.py:47-56` now enters the context manager before calling `setup()`:

```python
cm = AsyncPostgresSaver.from_conn_string(dsn)
checkpointer = await cm.__aenter__()
await checkpointer.setup()
setattr(checkpointer, "_ctx_manager", cm)
```

This fix is applied consistently to `create_postgres_checkpointer`, `create_redis_checkpointer`, and `create_dual_checkpointer`.

### 2.4 HermesBrain: lazy AIAgent factory is fixed

`src/life_kernel/hermes_brain.py:95-111` shows `_default_agent_factory` lazily imports `AIAgent` and returns an instance:

```python
def _default_agent_factory(**kwargs: Any) -> Any:
    AIAgent = _load_aiagent()
    return AIAgent(**kwargs)
```

This resolves the earlier `TypeError: 'AIAgent' object is not callable` / factory contract mismatch.

### 2.5 Main wiring: DSN from env, Discord REST Option B

`src/core/main.py:217-280` reads `DATABASE_URL`, strips `+asyncpg`, creates the checkpointer, builds the graph, and wires the `DashboardWriter` + `DiscordLogChannel`.

```python
_db_url = os.environ.get("DATABASE_URL", "postgresql://guinevere_core@localhost:5433/guinevere")
_checkpointer_dsn = _db_url.replace("postgresql+asyncpg://", "postgresql://")
checkpointer = await create_postgres_checkpointer(_checkpointer_dsn)
```

### 2.6 Core worker and guardian fixes are present

- `src/core/services/llm_metrics.py:86-93` wraps `start_http_server` in `try/except OSError` so the second uvicorn worker no longer crashes on port 9191.
- `src/loops/guardian.py:183-185` uses the correct property `self._hard_stop_handler.is_safe`.

### 2.7 Placeholders confirmed

- `src/life_kernel/graph.py:129` — `world_model_available = False  # Placeholder for P18 integration`
- `src/life_kernel/graph.py:463-468` — `idle_node` uses `random.choice` over three hardcoded task strings.
- `src/life_kernel/p16_adapter.py` and `src/life_kernel/p18_adapter.py` return mock data.
- `src/life_kernel/graph.py:159-170` builds `DecisionContextBuilder` only when `kg_adapter` and `memory_adapter` are injected into state; otherwise it falls back to a placeholder dict.

---

## 3. Live VPS Verification

### 3.1 Service state (2026-06-24)

Command run:

```bash
ssh -o ConnectTimeout=10 guinevere-vps 'systemctl show -p NRestarts --value -p ExecMainStatus --value guinevere-core.service; systemctl is-active guinevere-core.service; cat /etc/systemd/system/guinevere-core.service 2>/dev/null | grep -iE "workers|exec"; journalctl -u guinevere-core.service --since "1 hour ago" --no-pager 2>/dev/null | grep -iE "recursion|guardian|is_hard_stop_active|checkpointer|GraphRecursionError|dashboard_publish_failed|fallback" | tail -20'
```

Result:

```text
0
0
active
ExecStart=/home/guinevere/code/guinevere/.venv/bin/uvicorn src.core.main:app --host 127.0.0.1 --port 8000 --workers 2
```

No matches for any of the error patterns in the last hour.

### 3.2 Health checks

```bash
curl -s http://localhost:8000/health
curl -s http://localhost:8000/health/detailed
```

Results:

```json
{"status":"healthy","service":"guinevere-core","version":"0.1.0"}
{"service":"guinevere-core","version":"0.1.0","components":{"loop_manager":{"status":"ok","active_loops":0},"guardian":{"status":"ok"},"redis":{"status":"ok"},"postgresql":{"status":"ok"},"9router":{"status":"ok","models":63}}}
```

### 3.3 Other services undisturbed

```bash
systemctl is-active guinevere-9router guinevere-gmail guinevere-mcp guinevere-monitoring guinevere-whatsapp guinevere-x-poster cloudflared
```

All returned `active`.

---

## 4. Gap Table

| id | severity | title | current | required | files | vision-ref |
|---|---|---|---|---|---|---|
| gap-world-model-placeholder | medium | `world_model_available` is hardcoded False | `graph.py:129` sets `world_model_available = False` with no real substrate call | Inject P18 memory adapter and real memory recall; set flag based on availability | `src/life_kernel/graph.py`, `src/life_kernel/p18_adapter.py`, `src/core/main.py` | LK-010 / V-003 |
| gap-idle-task-hardcoded | low | `idle_node` uses only random hardcoded tasks | `graph.py:463-468` uses `random.choice` over 3 strings; ignores world model | Use `DecisionContextBuilder` + `hermes_brain.think()` to generate context-aware agenda items | `src/life_kernel/graph.py`, `src/life_kernel/decision_context.py` | V-003 |
| gap-decision-context-unwired | high | `decision_context` is never enriched with real P16/P18 data | `graph.py:159-170` only builds real context if adapters are in state; they are never injected | Inject `kg_adapter` and `memory_adapter` into `LifeMindState` and wire real recall | `src/life_kernel/graph.py`, `src/life_kernel/p16_adapter.py`, `src/life_kernel/p18_adapter.py`, `src/core/main.py` | LK-010 / V-003 |
| gap-sensor-loop-stub | low | `_heartbeat_30s` has no sensor integration | `heartbeat.py:414-415` is a comment-only placeholder | Register real sensor adapters in `SensorRegistry` and call `sense_all()` | `src/life_kernel/heartbeat.py`, `src/life_kernel/sensors.py`, `src/life_kernel/sensor_adapters/*.py` | LK-011 |
| gap-stuck-detection-stub | low | `_heartbeat_10s` has no graph stuck detection | `heartbeat.py:388-394` only logs a debug line | Track last phase transition timestamp; alert if same phase > threshold | `src/life_kernel/heartbeat.py`, `src/life_kernel/state.py` | LK-013 |
| gap-deep-scan-stub | low | `_heartbeat_5m` is comment-only | `heartbeat.py:544-545` placeholder | Query domain-mind health/status endpoints | `src/life_kernel/heartbeat.py`, `src/life_kernel/domain_minds/*.py` | LK-014 |
| gap-reflection-stub | low | `_heartbeat_1h` is comment-only | `heartbeat.py:566-567` placeholder | Trigger `self_improve` reflection, memory consolidation, and candidate generation | `src/life_kernel/heartbeat.py`, `src/life_kernel/self_improve.py` | LK-015 |

---

## 5. Risks

| risk | mitigation |
|---|---|
| Injecting real P16/P18 adapters into the graph could slow the 60s heartbeat if recall calls are slow or error-prone. | Wrap recall in `asyncio.wait_for` with a hard timeout; use the existing `_safe_think` / fallback patterns; keep mock adapters as no-op defaults. |
| Wiring `hermes_brain` into `idle_node` may increase 9Router token consumption. | Continue using the `QUIET_MODE=True` and `max_iterations=5` defaults; the operator has approved unlimited tokens, but the code already minimizes calls. |
| Enabling real sensors could leak operator data (email, finance, wearable) to logs or Discord. | Mark sensor output as `NotRequired` and do not write raw payloads to the dashboard/log; keep display-only autonomy. |
| A stale checkpoint could resurrect `hard_stop_requested=True` after Redis key is cleared. | Already handled by `_heartbeat_1s` recovery path (`heartbeat.py:326-350`). Verify after every deploy. |
| Graph recursion limit too low once additional nodes are added. | The current graph has at most 4 steps per cycle; 25 remains safe. Add a unit test asserting a compiled graph completes within 10 steps. |

---

## 6. Hard-Rejection Flags

None identified in the current codebase against the stated rules:

- No raw `LLMRouter.chat` path is used; autonomy goes through `HermesBrain.think` only.
- HARD STOP remains a non-LLM, absolute path in `decide_node` (`graph.py:211-213`) and the 1s heartbeat.
- Terminology uses "heartbeat" exclusively.
- No secrets are present in source; all credentials come from environment variables.
- Autonomy is display-only (dashboard + log) with no DMs or side-effects.

---

## 7. Concrete Recommendation for the Implementation Phase

### 7.1 Deploy path for the next code change

1. **Local prep**
   - Branch from `main`.
   - Run `pytest tests/life_kernel/ -q --disable-warnings --tb=short` until green.
   - Run forbidden-pattern scan if available.

2. **SCP / deploy changed files**
   - Use the existing VPS user and path, e.g.:
     ```bash
     scp src/life_kernel/graph.py guinevere-vps:/home/guinevere/code/guinevere/src/life_kernel/graph.py
     scp src/life_kernel/p18_adapter.py guinevere-vps:/home/guinevere/code/guinevere/src/life_kernel/p18_adapter.py
     # repeat for each changed file
     ```
   - Do not copy `.env` or secrets.

3. **Database migration**
   - `recall_memories` uses existing tables (`src/memory/read_pipeline.py`).
   - No Alembic migration is expected for P16/P18 recall wiring.
   - If a future change adds new tables, run on the VPS:
     ```bash
     cd /home/guinevere/code/guinevere
     source .venv/bin/activate
     alembic upgrade head
     ```

4. **Restart only `guinevere-core.service`**
   ```bash
   ssh guinevere-vps 'sudo systemctl restart guinevere-core.service'
   ```

5. **Smoke tests**
   ```bash
   curl -s http://localhost:8000/health
   curl -s http://localhost:8000/health/detailed
   ```

6. **Verify other 7 services remain active**
   ```bash
   systemctl is-active guinevere-9router guinevere-gmail guinevere-mcp guinevere-monitoring guinevere-whatsapp guinevere-x-poster cloudflared
   ```

### 7.2 Rollback path

```bash
ssh guinevere-vps
cd /home/guinevere/code/guinevere
git checkout -- src/life_kernel/graph.py src/life_kernel/p18_adapter.py  # etc.
sudo systemctl restart guinevere-core.service
```

### 7.3 HARD STOP regression test

On the VPS:

```bash
# Trigger
redis-cli -n 6 -a "$REDIS_PASSWORD" SET life_kernel:hard_stop 1 EX 120

# Verify
journalctl -u guinevere-core.service --since "1 minute ago" --no-pager | grep -E "hard_stop_detected|heartbeat_service_stopping"

# Confirm service stops or halts heartbeat; then clear and recover
redis-cli -n 6 -a "$REDIS_PASSWORD" DEL life_kernel:hard_stop
sudo systemctl restart guinevere-core.service
journalctl -u guinevere-core.service --since "1 minute ago" --no-pager | grep "heartbeat_liveness_check"
```

Expected:
- `hard_stop_detected_live` appears.
- `heartbeat_service_stopping task_count=6` appears.
- After `DEL` + restart, `heartbeat_liveness_check` resumes every ~1s.

---

## 8. Summary

The P20 kernel is **deployed and runtime-safe**. The five critical stabilization bugs are resolved on the VPS. The next phase should focus on closing the **decision-context wiring gap (high severity)** by injecting real P16/P18 adapters into `LifeMindState` and enriching `observe_node` and `idle_node`, while keeping every safety boundary (HARD STOP non-LLM, display-only autonomy, no secrets in source) intact. All other gaps are lower-priority stub implementations behind the existing heartbeat hooks.
