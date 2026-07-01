# Load Test Results — 100 Subagent Burst

**Date**: 2026-06-27 14:43-14:46 WIB  
**Method**: 100 real Claude Code Agent tool calls via Workflow `parallel()`, each routing through `ANTHROPIC_BASE_URL=http://100.104.210.75:20128/v1`  
**Model**: `subagent` (9Router combo → Claude API)  
**Prompt**: Heavy read (200-400 chars code review prompts, diverse languages)  
**max_tokens**: N/A (agent decides output length)

---

## Results

| Metric | Value |
|---|---|
| Total agents | 100 |
| Succeeded | **100** (100%) |
| Failed | **0** (0%) |
| OK-pattern replies | 93 |
| Non-OK replies | 7 |
| Workflow duration | ~240 seconds |
| Sustained throughput | **~25 requests/minute (RPM)** |

## Error Classification

| Error Type | Count |
|---|---|
| Client timeout | 0 |
| 9Router error (5xx) | 0 |
| Upstream provider error | 0 |
| Connection refused | 0 |
| Agent returned null | 0 |
| **Total errors** | **0** |

## Status Distribution

All 100 agents completed successfully. No HTTP-level errors (agents returned valid string responses).

## VPS Impact

| Metric | Before | After |
|---|---|---|
| RAM available | 3388MB | 3346MB |
| Load average | 0.02 | 0.11 |
| PM2 restarts | 4 | 4 |
| PM2 CPU | 0% | 0% |

## Bottleneck Analysis

| Component | Status |
|---|---|
| **9Router (VPS)** | ✅ **Not saturated.** CPU 0%, RAM +42MB, no restarts. Capable of far more. |
| **Workflow concurrency cap** | ⚠️ Internal cap ~10-16 simultaneous agents. This limits true 100-concurrent hit. |
| **Upstream (Claude API)** | ❓ Likely rate-limited. Each agent waits for upstream response before completing. |

## Verdict

**P9Router PASS** — 100% success rate, zero failures, zero VPS impact.  
**RPM produced: 25 RPM** (limited by workflow concurrency cap + upstream API latency, not 9Router itself).
