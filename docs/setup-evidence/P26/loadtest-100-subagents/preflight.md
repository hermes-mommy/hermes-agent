# P26 Load Test Preflight — 9Router VPS

**Date**: 2026-06-27 14:27 WIB  
**Test**: 100+ Concurrent Subagent Load Against 9Router VPS  
**Host**: `100.104.210.75:20128` (via Tailscale)  
**VPS SSH**: `root@49.12.82.34:39999`  
**Target Model**: `subagent` (combo)

---

## Preflight Checklist

### 1. AGENTS.md Read ✅
- Operating contract reviewed. Workflow Faiz: research > preflight > planning > execution > audit > fix > re-audit > final.
- TEST ONLY mandate: no config mutation, no service restart, no firewall change, no provider/key change.

### 2. Documents Read ✅
- `docs/setup-evidence/P25/p25-replan.md` — 9Router VPS migration plan (service user root, systemd, Tailscale)
- `docs/setup-evidence/P26/p26-implementation.md` — PM2 cluster mode evidence
- `docs/setup-evidence/P26/9router-hightraffic-tuning-2026-06-27.md` — PM2 NOFILE 65535, backlog 4096, Tailscale userspace

### 3. Endpoint Verification ✅

**From Windows (via Tailscale):**
```
GET http://100.104.210.75:20128/v1/models
→ {"object":"list","data":[{"id":"orcestrator","owned_by":"combo"},{"id":"subagent","owned_by":"combo"},...]}
```
Models available: orcestrator, subagent, gpt, tester, qoder, kiro, router9, opencode, cmc, and others.

**From VPS localhost:**
```
GET http://127.0.0.1:20128/v1/models
→ Same JSON response verified ✅
```

### 4. PM2 State ✅

| Metric | Value |
|---|---|
| Workers | 2 online (PID 31108, 31121) |
| Restarts | 4 (since deployment, stable) |
| RAM/worker | 257MB / 319MB |
| CPU | 0% idle |
| Uptime | 4h |
| pm2-root.service | active |
| pm2-logrotate | online |

### 5. VPS System Resources ✅

| Metric | Value |
|---|---|
| CPU | Load avg: 0.01, 0.07, 0.11 |
| RAM total | 4000MB |
| RAM free | 2182MB |
| RAM available | 3394MB |
| RAM used | 605MB |
| VPS uptime | 1 day 1:39 |
| tailscaled | active ✅ |

### 6. API Key Source ✅
API key found in `settings.json` and `opencode.json` (truncated: `sk-dfe2d...`). Key will be used in-memory for test requests. **No secrets will be written to output files.**

### 7. Hard Stop Criteria Baseline

| Criterion | Current State | Threshold |
|---|---|---|
| 9Router reachable | ✅ Reachable | Must stay reachable |
| PM2 restart count | 4 total (stable) | Must not increase during test |
| tailscaled | ✅ Active | Must stay active |
| RAM available | 3394MB | Must not drop below 500MB |
| VPS load | 0.01 | Must not exceed CPU capacity |
| SSH stability | ✅ Stable | Must remain responsive |

---

## Preflight Verdict

**READY FOR LOAD TEST** ✅

All preflight checks pass:
- Endpoint responsive
- PM2 healthy
- VPS resourced (3.4GB available RAM, load 0.01)
- API key available
- No hard stop criteria triggered
