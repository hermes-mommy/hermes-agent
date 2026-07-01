# Fix Log — Audit Round 1 Findings

**Date**: 2026-06-27

---

## Issue 1: True Concurrency Limitation
**Severity**: HIGH  
**Fix**: Document explicitly. Workflow `parallel()` has internal cap of ~10-16 simultaneous agents. This is a harness limitation, not a 9Router limitation. For true 100-concurrent burst, external tooling (Python aiohttp or 100 independent Agent tool calls) would bypass this.

**Resolution**: Documented in results and final report.

## Issue 2: Missing Per-Request Latency
**Severity**: MEDIUM  
**Fix**: Computed overall throughput from wall clock. VPS timestamps:
- Workflow start (VPS before): 07:43:08 UTC
- Workflow end (VPS after): 07:46:39 UTC
- Total wall duration: 211 seconds (~3.5 min)
- Effective throughput: 100 / 211 = **28.4 RPM**

Per-request latency unavailable because each subagent's timing is internal to the Workflow harness.

**Resolution**: RPM recalculated from actual timestamps. Per-request metrics documented as unavailable.

## Issue 3: Missing p50/p90/p95/p99
**Severity**: MEDIUM  
**Fix**: Cannot retroactively compute. Added as caveat.

## Issue 4: RPM Based on Wall Clock
**Severity**: LOW  
**Fix**: Recalculated: 28.4 RPM from actual VPS timestamps. Labeled as "effective throughput under Workflow parallel cap."
