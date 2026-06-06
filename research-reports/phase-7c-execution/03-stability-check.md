# Stability Check — Phase 7c Deprecated Archive Gate

**Report**: research-reports/phase-7c-execution/03-stability-check.md
**Date**: 2026-06-06 18:30 WIB
**Operator**: Guinevere (sub-agent)
**Method**: SSH read-only to guinevere-vps (systemctl, journalctl)

---

## Verdict

**24h Stability Gate: FAIL** — No Guinevere service has achieved 24h continuous uptime.

**Deprecated Archive Safety: NOT YET SAFE** — Wait until at least 2026-06-07 12:35 WIB for current instance to reach 24h.

---

## 1. System Overview

| Property | Value |
|---|---|
| Host | faiz-prod-01 |
| System boot | 2026-05-23 10:35 |
| System uptime | 14 days continuous |
| Boot journal | 1 boot since 2026-06-04 (no reboots) |
| Memory | 15Gi total, 4.3Gi used, 10Gi available — no pressure |
| OOM kills | None detected |

---

## 2. Service Status Summary

| Service | Status | Active Since | NRestarts | Uptime |
|---|---|---|---|---|
| hermes-gateway | active/running | 2026-06-06 12:35:31 WIB | 0 | 5h 46min |
| guinevere-core | active/running | 2026-06-06 12:35:31 WIB | 0 | 5h 46min |
| guinevere-loops | active/running | 2026-06-06 12:35:31 WIB | 0 | 5h 46min |
| guinevere-surveillance | active/running | 2026-06-06 12:35:31 WIB | 0 | 5h 46min |
| guinevere-scheduler | active/running | 2026-06-06 12:35:31 WIB | 0 | 5h 46min |
| guinevere-9router | active/running | 2026-06-01 08:21:12 WIB | 0 | **5+ days** |
| guinevere-monitoring | active/running | 2026-06-03 10:26:50 WIB | 0 | **3+ days** |
| guinevere-mcp | **inactive/dead** | N/A | N/A | **Disabled** |

**All services** have `Restart=always` with `RestartSec=10`. Surveillance also has `StartLimitBurst=5` within 300s.

---

## 3. Stability History — hermes-gateway

### June 5 (17 restarts)

| Time Span | Duration | Notes |
|---|---|---|
| 07:55 – 08:26 | 31 min | MCP config errors + Discord connect failure |
| 08:26 – 08:34 | 8 min | Same pattern |
| 08:34 – 09:23 | 49 min | Stabilizing |
| 09:23 – 13:17 | Multiple rapid restarts (cluster) | MCP config loop |
| **13:17 – 21:24** | **~8h 7min** | **Longest stable run** (PID 3483297, 462 log lines) |
| 21:24 – 21:25 | 1.5 min | Brief restart |

**Best run**: ~8h (13:24 to 21:24)

### June 6 (9 restarts before 12:35)

| Time Span | Duration | Notes |
|---|---|---|
| 02:48 – 08:45 | **~5h 57min** | **2nd longest run** |
| 08:45 – 12:00 | Multiple rapid restarts (cluster) | **pgvector import crash** (see §3.1) |
| 12:00 – 12:35 | ~35 min | Transition to current instance |
| **12:35 – present** | **~5h 46min** | **Current run, ongoing, NRestarts=0** |

### Post-12:35 Error Profile (current instance)

| Metric | Count |
|---|---|
| Error/Traceback/Exception matches | 30 |
| "discord failed to connect" | 0 |
| "Hermes Gateway Starting" (restarts) | **1** (the initial start) |
| API auth errors | Present (Redis AUTH, codex/gpt-5.5 401) — non-fatal |
| MCP config WARNINGs | Present (web/filesystem/terminal/git/fetch missing 'command') — non-fatal |
| Shell hook WARNINGs | Present (consent_gate.py, budget_check.py, dnr_filter.py missing) — non-fatal |

---

## 4. Stability History — guinevere-core

### Issues
- **11,906 error/traceback matches** since 12:35 — all uvicorn worker port conflicts
- Root cause: `start_llm_metrics_server(port=9191)` in `src/core/services/llm_metrics.py` binds port 9191 during startup. With `--workers 2`, the second worker fails because port 9191 is already taken by the first worker.
- **Non-fatal**: The main process and first worker serve traffic normally. ~10 failures/minute is expected noise.
- No actual service restarts (NRestarts=0).

### Pre-12:35 History
- Previous instance was running before 12:33 (port conflict at 12:33:55 when someone tried to start another instance)
- Journalctl history queries timed out (>120s) due to log volume — service has extensive logging

---

## 5. Stability History — guinevere-loops & guinevere-surveillance

| Aspect | Result |
|---|---|
| Post-12:35 errors | **0** (completely clean) |
| June 5-6 pre-restart errors | 8 each — all `ModuleNotFoundError: No module named 'pgvector'` |
| Root cause | Import chain: `src/loops/manager.py` → ... → `src/memory/models.py` → `from pgvector.sqlalchemy import Vector` → **ModuleNotFoundError** |
| Crash cluster | 11:48-11:49 on June 6, caused 6 rapid restarts across both services |
| Current status | Running stable since 12:35 without errors |

---

## 6. Key Blocker — guinevere-mcp

**Status**: `inactive (dead)`, `disabled`
**Last run**: 2026-06-04 14:17:04 (shut down cleanly)
**Phase 7b B1 blocker** — must be resolved before deprecated archive can proceed.

---

## 7. Stable Services (Unaffected)

| Service | Uptime | Notes |
|---|---|---|
| guinevere-9router | 5+ days | Continuously serving since Jun 1 |
| guinevere-monitoring | 3+ days | Prometheus/Grafana/Loki stack stable since Jun 3 |
| cloudflared | — | Cloudflare Tunnel for Discord webhook — stable |

These services are independent of the 24h stability gate and do not block archive.

---

## 8. Blockers Summary

| ID | Blocker | Severity | Status |
|---|---|---|---|
| **B1** | **guinevere-mcp inactive/disabled** | **BLOCKING** | Unchanged from Phase 7b |
| **B2** | **No service has 24h continuous uptime** | **BLOCKING** | Max observed: ~8h (hermes-gateway, Jun 5) |
| B3 | pgvector dependency crash on import | HIGH | Triggered rapid restarts on Jun 6 11:48. Fixed by 12:35 (package installed or import path bypassed). Root cause unclear. |
| B4 | Uvicorn worker port 9191 conflict (prometheus metrics) | LOW | Non-fatal noise. ~10 failures/min expected with `--workers 2`. |
| B5 | Missing shell hook scripts (consent_gate.py, budget_check.py, dnr_filter.py) | LOW | Non-fatal WARNINGs on every tool call. |

---

## 9. Stability Trends

```
Jun 5 00:00 ──────────────────────────────────────────
         07:55 ──┤ 31m ├── 8m ├── 49m ├── [cluster] ─┤ 8h 7m ├──┤
Jun 6 00:00 ──────────────────────────────────────────
         02:48 ───────────── 5h 57m ────────────┤ cluster(pgvector) ├──┤ 5h 46m+ ┤
```

- **Improving**: Current run (5h 46min+) is the 2nd longest observed. No restarts since 12:35.
- **Morning fragility**: Both days show instability clusters in morning (07:00-10:00).
- **Afternoon/evening stability**: Service tends to stabilize after 12:00-13:00.

---

## 10. When to Proceed

If the current instance (started 12:35 WIB) continues without restart:

| Checkpoint | Time | Status |
|---|---|---|
| Current uptime | 5h 46min | Stable, NRestarts=0 |
| **24h gate** | **2026-06-07 12:35 WIB** | **Minimum required** |
| 48h gate | 2026-06-08 12:35 WIB | Desired before archive |

**Recommendation**: Re-check at 2026-06-07 13:00 WIB. If all services still running with NRestarts=0, stability gate PASSES.

---

## 11. Caveats

1. This report captures a snapshot at 18:30 WIB on 2026-06-06. Stability status may change.
2. Journalctl history queries for guinevere-core timed out (>60s) due to log volume — history analysis for core is incomplete.
3. pgvector `pip install` status could not be verified (sudo password prompt on SSH).
4. The 12:35 restart was service-level (not system reboot). Likely a manual `systemctl restart` for the stack.
5. "Address already in use" errors in hermes-gateway pre-12:35 and core post-12:35 are from different mechanisms (core: prometheus port 9191; hermes: port binding race).
