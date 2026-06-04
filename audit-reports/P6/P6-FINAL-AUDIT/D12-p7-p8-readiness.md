# D12 — P7/P8 Readiness Audit

**Auditor:** Guinevere (autonomous)  
**Date:** 2026-06-03  
**Scope:** P6 foundation assessment for P7 (Surveillance) and P8 (Observability)  
**Verdict:** **READY WITH CAVEATS**

---

## Readiness Matrix

| # | Dimension | Verdict | Confidence | Notes |
|---|-----------|---------|------------|-------|
| 1 | MCP tool module extensibility | ✅ **PASS** | High | `register_all_tools()` pattern is clean, documented, 16 tools prove it |
| 2 | Observability/metrics hooks | ⚠️ **NEEDS REVIEW** | High | Zero Prometheus integration in `src/mcp/` — blocking for P8-005 |
| 3 | Cost tracking → API readiness | ⚠️ **NEEDS REVIEW** | High | Data layer exists (DB5) but no HTTP endpoint to serve `/cost` / `/budget` |
| 4 | Auth matrix extensibility | ✅ **PASS** | High | Flat `dict[str, dict[str, AuthLevel]]` — trivial to add entries |
| 5 | Redis DB allocation (no conflict) | ✅ **PASS** | High | DB2 pre-allocated for surveillance; DB5 for cost; no overlap |
| 6 | systemd service template | ✅ **PASS** | High | Hardened, documented template with resource limits and security directives |
| 7 | Evidence/scaffold pattern | ✅ **PASS** | High | 11-section batch plan + per-step scaffold.md → verification.md → auditor-gate.md |

**Overall:** 5 PASS / 2 NEEDS REVIEW / 0 FAIL

---

## Dimension Analysis

### 1. MCP Tool Module Extensibility — ✅ PASS

**Current state** (`src/mcp/tools/__init__.py`):
- `register_all_tools(server: FastMCP) -> int` iterates `_TOOL_MODULES`, calls each module's `register_tools(server)` entry-point.
- 16 tool modules already registered: `brave_search`, `context7`, `docker_tool`, `exa_search`, `fetch`, `filesystem`, `git_tool`, `github`, `grep_app`, `obscura_cdp`, `postgres_tool`, `redis_tool`, `sequential_thinking`, `shell_tool`, `time_tools`, `websearch`.
- Docstring explicitly states the extension pattern: "When a new tool module is added to this package, import it here and call its `register_tools` function."

**P7 impact:** Adding a `surveillance_tool.py` (exposing `/surveillance-status`, `/surveillance-pause`, etc.) requires 3 lines:
```python
from src.mcp.tools import surveillance_tool
_TOOL_MODULES.append(surveillance_tool)
```
No architectural changes needed.

**P8 impact:** Adding metrics-query tools (e.g., `prometheus_tool.py` for `/cost` queries) follows the same pattern.

---

### 2. Observability/Metrics Hooks — ⚠️ NEEDS REVIEW

**Current state:** `grep` for `prometheus`, `metrics`, `prometheus_client` across `src/mcp/` returned **zero matches**. The MCP server (`manager.py`) is a stdio-based FastMCP gateway — it runs via `server.run()` without any HTTP port. There is no `/metrics` endpoint, no Prometheus `Counter`/`Gauge`/`Histogram`, no middleware to track tool invocation counts or latencies.

**P8 requirement** (StepPrompts §P8-005):
```yaml
- job_name: 'guinevere-core'
  static_configs: [{targets: ['host.docker.internal:8000']}]
  metrics_path: /metrics
```
P8-005 expects a `/metrics` endpoint on port 8000. The MCP server doesn't expose one. The core API (FastAPI on 8000) may exist from earlier phases, but MCP tool metrics (invocation count, latency, auth denials, cost events) need to be instrumented at the MCP layer.

**Gap:** P6 has zero observability hooks. P8 cannot scrape MCP tool metrics without adding instrumentation.

**Pre-P7 fix:** Add a lightweight metrics module (e.g., `src/mcp/metrics.py`) with:
- `COUNTER tool_invocations_total{tool_name, auth_level, status}`
- `HISTOGRAM tool_latency_seconds{tool_name}`
- `COUNTER auth_denials_total{tool_name, reason}`
- Expose via FastAPI core or a dedicated metrics port.

---

### 3. Cost Tracking → API Readiness — ⚠️ NEEDS REVIEW

**Current state:**

| Module | Status | Capability |
|--------|--------|------------|
| `src/mcp/cost.py` | ✅ Implemented | `ToolCostTracker` — `record_tool_cost()`, `get_all_daily_costs()`, `get_tool_monthly_cost()` |
| `src/mcp/budget.py` | ✅ Implemented | `BudgetEnforcer` — `check_budget()`, `get_fallback_tool()`, `get_monthly_status()` |
| `src/mcp/manager.py` | ❌ Not wired | Neither `ToolCostTracker` nor `BudgetEnforcer` is instantiated or called |
| HTTP endpoint | ❌ Missing | No `/cost` or `/budget` route exists |

Both modules are fully written and well-structured but are **dead code** — they exist as importable classes with zero callers. P8-017 (`/cost` command) and P8-018 (`/budget` command) require these to be wired into a FastAPI endpoint that Discord commands can query.

**P8 requirement** (StepPrompts §P8-017/P8-018):
> `/cost` Command — Daily spend breakdown in Discord  
> `/budget` Command — Monthly projection and remaining budget

These commands need something like:
```python
# src/api/routes/cost.py
@router.get("/api/cost/daily")
async def get_daily_costs():
    tracker = ToolCostTracker()
    return tracker.get_all_daily_costs()
```

**Pre-P7 fix:** Wire `ToolCostTracker` + `BudgetEnforcer` into the FastAPI core (port 8000) with `/api/cost/` routes, or into a dedicated MCP REST endpoint. Also wire `record_tool_cost()` calls into the auth decorator or tool dispatch path so costs are actually recorded.

---

### 4. Auth Matrix Extensibility — ✅ PASS

**Current state** (`src/mcp/auth_matrix.py`):
- `AUTH_MATRIX: Final[dict[str, dict[str, AuthLevel]]]` — flat dict with 16 tools and operation→auth-level mappings.
- `ALL_TOOL_NAMES` — canonical ordered tuple.
- `get_auth_level(tool_name, operation)` — lookup with `KeyError` on miss, supporting `"*"` wildcard.
- `verify_matrix_completeness()` — assertion gate that logs missing/extra tools.

**P7 impact:** Adding surveillance tools (e.g., `surveillance_status`, `surveillance_pause`):
```python
"surveillance_status": {
    "read": AuthLevel.READ_AUTO,
},
"surveillance_pause": {
    "toggle": AuthLevel.WRITE_NOTIFY,
},
```
Plus append to `ALL_TOOL_NAMES`. Pattern is trivially scalable — no architectural bottleneck.

---

### 5. Redis DB Allocation — ✅ PASS

**Current state** (documented in `src/mcp/tools/redis_tool.py` docstring + `cost.py`/`budget.py`):

| DB | Allocation | Phase | Consumer |
|----|-----------|-------|----------|
| DB0 | Session cache | P5 | Agent loop |
| DB1 | Memory recall | P5 | Memory subsystem |
| DB2 | **Surveillance buffer** | **P7** | FastAPI receiver → consumer → TimescaleDB |
| DB3 | Agent state | P5 | Agent loop |
| DB4 | Discord state | P5 | Discord bot |
| DB5 | Cost tracking | P6 | `ToolCostTracker`, `BudgetEnforcer` |

**P7 requirement:** Steps P7-001 through P7-008 specify Redis DB2 for the surveillance buffer (`surveillance:buffer` list). This slot is **pre-allocated and uncontested**. DB5 (cost tracking) and DB2 (surveillance) are separate logical databases — no conflict at the Redis server level.

**Zero conflicts.**

---

### 6. Systemd Service Template — ✅ PASS

**Current state** (`systemd/guinevere-mcp.service`):

Pattern includes every element needed by P7/P8:

| Field | Value | P7/P8 Reuse |
|-------|-------|-------------|
| `[Unit] Description` | Specific to service | Adapt per service |
| `After=` | `guinevere-core.service network.target` | Same pattern |
| `Requires=` | `guinevere-core.service` | Extendable |
| `Type=` | `exec` | Same |
| `User=` | `guinevere` | Same |
| `WorkingDirectory=` | `/home/guinevere/code/guinevere` | Same |
| `ExecStart=` | `.venv/bin/python -m src.mcp.manager` | Adapt entry-point |
| `Restart=` | `always` | Same |
| `RestartSec=` | `10` | Same |
| `Slice=` | `guinevere.slice` | Same |
| `MemoryHigh/Max` | `1G` / `2G` | Tune per service |
| `CPUQuota=` | `200%` | Tune per service |
| `NoNewPrivileges=` | `true` | Same |
| `ProtectSystem=` | `strict` | Same |
| `ProtectHome=` | `read-only` | Same |
| `ReadWritePaths=` | Specific directories | Adapt per service |

P7's `guinevere-surveillance.service` (StepPrompts §P7-018) already follows this exact template. P8's `guinevere-monitoring.service` (P8-021) will do the same.

---

### 7. Evidence/Scaffold Pattern — ✅ PASS

**Current state** (`docs/setup-evidence/P6/`):

The batch-plan-001-021.md establishes a reusable 11-section template:
1. (a) Master Todo with parallelism markers
2. (b) Dependency Map (graph + table)
3. (c) Parallelism Map
4. (d) Collision Scan
5. (e) Research Inputs
6. (f) Known State
7. (g) Binding Decisions
8. (h) Evidence Paths (per step)
9. (i) Auditor Matrix
10. (j) Rollback Plan
11. (k) Caveats + Execution Checklist

Per-step scaffold (`scaffold.md`) defines:
- Expected Files
- Forbidden Patterns (regex-verifiable)
- Required Commands (with expected exit codes)
- Implementation Details (code snippets)
- Evidence Requirements (verification.md + auditor-gate.md)
- Hard Rejection Criteria (binary PASS/FAIL checklist)

P7 StepPrompts already specify evidence paths under `docs/setup-evidence/P7/STEP-P7-XXX/`. P8 follows the same convention.

**P7/P8 reuse:** Copy the batch-plan template, adapt the 11 sections, generate per-step scaffolds.

---

## Blocking Gaps

### For P7 (Surveillance)

| # | Gap | Severity | Blocking? |
|---|-----|----------|-----------|
| G1 | No metrics instrumentation in MCP layer | Low | ❌ Not blocking P7 — surveillance operates independently |
| G2 | No cost-wiring audit trail — surveillance tool costs won't be tracked | Low | ❌ Non-blocking; P7 can proceed without cost tracking |
| G3 | `src/surveillance/` directory does not exist | High | ❌ Expected; P7 creates it |

**Verdict:** No blocking gaps for P7. P6 provides everything P7 needs (MCP extensibility, Redis DB2 allocation, systemd template, evidence pattern).

### For P8 (Observability)

| # | Gap | Severity | Blocking? |
|---|-----|----------|-----------|
| G1 | No `/metrics` endpoint in MCP server | **High** | ⚠️ **Blocking** — P8-005 expects `guinevere-core:8000/metrics` |
| G2 | `ToolCostTracker` / `BudgetEnforcer` not wired to HTTP | **High** | ⚠️ **Blocking** — P8-017/P8-018 need `/cost` and `/budget` commands |
| G3 | No tool invocation metrics (counters, latency) | Medium | ❌ Not blocking but significantly reduces observability value |
| G4 | `record_tool_cost()` never called from tool dispatch | Medium | ❌ Non-blocking for `/cost` display but costs won't be accurate |

**Verdict:** Two blocking gaps (G1, G2) must be resolved before P8 begins.

---

## Recommended Pre-P7 Fixes (Priority Ordered)

| Priority | Fix | Effort | Phase Target | Rationale |
|----------|-----|--------|-------------|-----------|
| **P0** | Add `src/mcp/metrics.py` with Prometheus `Counter`/`Gauge`/`Histogram` for tool invocations, latency, auth events | Short (1-4h) | P6 post-audit | Unblocks P8-005; also benefits P7 surveillance monitoring |
| **P0** | Wire `ToolCostTracker.record_tool_cost()` into the `@require_approval` decorator (post-execution hook) | Short (1-4h) | P6 post-audit | Ensures costs are actually recorded before P8 consumes them |
| **P0** | Create FastAPI cost routes (`/api/cost/daily`, `/api/cost/monthly`, `/api/budget/status`) wired to existing `ToolCostTracker` + `BudgetEnforcer` | Short (1-4h) | P6 post-audit | Unblocks P8-017 `/cost` command and P8-018 `/budget` command |
| **P1** | Add documentation comment in `tools/__init__.py` showing exact steps for P7 to add a surveillance tool module | Quick (<1h) | P6 post-audit | Reduces P7 implementation friction |
| **P1** | Create `src/surveillance/__init__.py` stub with docstring outlining P7 module structure | Quick (<1h) | Pre-P7 | Signals readiness to P7 implementation |

---

## Overall Readiness Score

### **READY WITH CAVEATS** (3 blocking gaps for P8; 0 for P7)

**P7 can begin immediately.** The MCP extensibility pattern, Redis DB2 pre-allocation, systemd template, and evidence/scaffold patterns are all production-ready.

**P8 requires 3 pre-requisite fixes** (all tagged P0 above):
1. Add Prometheus metrics instrumentation to `src/mcp/`
2. Wire `record_tool_cost()` into the tool dispatch path
3. Create `/api/cost/` and `/api/budget/` FastAPI routes

Total pre-P8 effort: **~Short (4-12h)** across all three fixes — achievable in one session before P7 completes.

### Recommendation

Execute the three P0 fixes immediately (post-P6 audit remediation). P7 runs in parallel with P8 pre-requisite work since they touch different areas (surveillance modules vs. metrics/cost wiring). By the time P7's 22 steps complete, P8's foundation will be ready.

---

*Audit report generated by Guinevere D12 auditor. 2026-06-03.*