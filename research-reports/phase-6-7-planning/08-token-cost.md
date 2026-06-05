# Phase 6-7 Planning: LLM Routing Token Cost & Benchmark Methodology

**Date**: June 5, 2026  
**Scope**: 9Router proxy configuration, model pricing analysis, and load testing methodology for Phase 6 migration.

---

## 1. Model Pricing Comparison (2026)

| Model | Input (Cache Miss) | Input (Cache Hit) | Output | Context Window | Notes |
|---|---|---|---|---|---|
| **DeepSeek V4 Flash** | $0.14 / 1M | $0.0028 / 1M | $0.28 / 1M | 1M tokens | Primary workhorse. 98% discount on cache hits. |
| **GPT-5.5** | $5.00 / 1M | $0.50 / 1M | $30.00 / 1M | 1M tokens | Quality fallback. Batch/Flex pricing at 50% discount. |
| **GPT-4o** *(Reference)* | $2.50 / 1M | $1.25 / 1M | $10.00 / 1M | 128K tokens | Legacy quality fallback reference. |
| **Guinevere Combo** | *Varies* | *Varies* | *Varies* | *Varies* | Balanced fallback (routes to cheap tiers like GLM ~$0.60/1M or MiniMax ~$0.20/1M via 9Router). |

*Note: DeepSeek V4 Pro is available at $0.435/$0.87 per 1M tokens (75% promo until May 31, 2026), rising to $1.74/$3.48 thereafter.*

---

## 2. Monthly Cost Projections

*Assumptions: 70% input / 30% output token ratio, with a 50% cache hit rate on input tokens.*

| Monthly Volume (Tokens) | DeepSeek V4 Flash | GPT-5.5 | GPT-4o *(Reference)* | Savings (vs GPT-5.5) |
|---|---|---|---|---|
| **10M** (Solo Dev) | ~$1.34 | ~$109.25 | ~$43.13 | ~98.8% |
| **100M** (Startup) | ~$13.40 | ~$1,092.50 | ~$431.25 | ~98.8% |
| **1B** (Enterprise) | ~$134.00 | ~$10,925.00 | ~$4,312.50 | ~98.8% |

*Calculation basis for 10M tokens (7M input @ 50% cache hit, 3M output):*
- **DeepSeek**: (3.5M × $0.0028) + (3.5M × $0.14) + (3M × $0.28) = $0.0098 + $0.49 + $0.84 = **$1.34**
- **GPT-5.5**: (3.5M × $0.50) + (3.5M × $5.00) + (3M × $30.00) = $1.75 + $17.50 + $90.00 = **$109.25**
- **GPT-4o**: (3.5M × $1.25) + (3.5M × $2.50) + (3M × $10.00) = $4.375 + $8.75 + $30.00 = **$43.13**

---

## 3. 9Router Pricing & Routing Model

- **License & Cost**: 100% Free and Open Source (MIT). **No transaction fees**, no per-request overhead.
- **Routing Strategy**: Smart 3-tier fallback (`Subscription` → `Cheap` → `Free`).
  - **Tier 1**: Premium subscriptions (Claude Code, Codex, GPT-5.5).
  - **Tier 2**: Cheap providers (GLM ~$0.60/1M, MiniMax ~$0.20/1M, Kimi).
  - **Tier 3**: Free providers (iFlow, Qwen, Kiro).
- **Token Optimization**: 
  - **RTK Token Saver**: Auto-compresses tool results (git diffs, grep outputs), saving 20–40% on input tokens.
  - **Caveman Mode**: Up to 65% output token reduction for specific workflows.
- **Overhead**: Negligible local proxy latency (<10ms). Runs at `http://localhost:20128/v1`.

---

## 4. LLM Benchmark Methodologies

### Quality Benchmarks
- **HumanEval+ / MBPP+**: Code generation accuracy (pass@1).
- **SWE-bench Lite**: Multi-file refactoring and real-world issue resolution.
- **MMLU / GSM8K**: General knowledge and mathematical reasoning.

### Performance Metrics
- **Time to First Token (TTFT)**: Critical for interactive UX. Target: **<500ms** (chat), **<200ms** (copilot). Measures prefill latency.
- **Time Per Output Token (TPOT) / Inter-Token Latency (ITL)**: Decode speed. Target: **>15 tok/s** for a responsive feel.
- **Throughput**: Total tokens per second (TPS) across concurrent requests. *Requests Per Second (RPS) is a misleading proxy for LLMs due to variable output lengths.*
- **Latency Percentiles**: p50, p95, p99. **p99 is critical** for detecting queuing, garbage collection, or OOM-related stalls.

### Recommended Tools
- **LLMPerf (Ray)**: Purpose-built for LLM token-level metrics; supports configurable input/output token distributions.
- **NVIDIA GenAI-Perf**: Excellent for concurrency sweeps and saturation point discovery; deep TensorRT-LLM integration.
- **k6 (with LLM extensions)**: Best for CI/CD integration and high-concurrency HTTP load testing (Go-based, avoids Python GIL bottlenecks).
- **Locust (with LLM-Locust)**: Python-based, good for custom scenario scripting, but beware of GIL bottlenecks at >1,000 QPS.
- **Vegeta**: Raw HTTP load testing for simple, high-volume stateless endpoint hammering.

---

## 5. Load Testing Plan Outline (10+ Concurrent Users)

### Phase 1: Workload Modeling
1. **Realistic Prompt Corpus**: Sample real production logs (scrubbed of PII) to reflect true input length distribution (e.g., 20% short, 50% medium, 30% long context).
2. **Multi-Turn State**: Simulate conversational sessions where context accumulates (e.g., 10 turns = ~8K tokens), as TTFT degrades significantly with context length.

### Phase 2: Metric Instrumentation
1. **Separate TTFT and TPS**: Instrument the test client to record the timestamp of the first byte received (TTFT) separately from the final byte (to derive TPS).
2. **Cache Testing**: Run distinct test batches for **cold cache** vs. **warm cache** to measure the true impact of DeepSeek's 98% cache-hit discount on routing economics.

### Phase 3: Concurrency Sweeps
1. **Fine-Grained Steps**: Do not jump from 10 to 50 users. Step through **10, 20, 30, 40, 45, 50**. KV cache saturation is non-linear; 45 users might catastrophically degrade TTFT compared to 40.
2. **Connection Pool Sizing**: Size HTTP connection pools to match expected concurrency + 20% headroom. For LLM APIs, the bottleneck is GPU KV cache, not CPU threads. Keep idle connections alive to avoid TLS handshake overhead on every request.

### Phase 4: Soak Testing
1. **Duration**: Run sustained load tests for **≥4 hours** at 80% of the discovered saturation concurrency.
2. **Monitor**: Watch for gradual memory leaks, KV cache fragmentation, and connection pool exhaustion (canonical symptoms: periodic TTFT spikes, slowly growing ITL).

### Phase 5: Mocking for App-Level Testing
- Use **mock LLM services** that simulate realistic TTFT/ITL distributions without consuming actual tokens or hitting rate limits during application logic load testing. Reserve live provider testing for final capacity validation.

---

## 6. Model Comparison & Routing Strategy

| Dimension | DeepSeek V4 Flash | GPT-5.5 / GPT-4o | Routing Recommendation |
|---|---|---|---|
| **Latency (TTFT)** | ~1.8s | ~0.4s | Route interactive/copilot requests to GPT-5.5. |
| **Throughput** | ~38 tok/s | ~82 tok/s | Route long-form generation to GPT-5.5 if speed is critical. |
| **Code/Reasoning** | Excellent (Chain-of-thought) | Excellent (Compressed) | DeepSeek excels at multi-step architectural reasoning. |
| **Cost Efficiency** | **~35–100x cheaper** | Premium pricing | Route high-volume batch/CI tasks to DeepSeek V4 Flash. |
| **Ecosystem** | Growing, self-hostable | Mature, SLA-backed | Use GPT-5.5 for enterprise compliance/SOC2 requirements. |

### Recommended 9Router Configuration for Phase 6
1. **Primary Route**: `deepseek-v4-flash` (leverage 9Router's RTK to maximize the 98% cache-hit discount).
2. **Quality Fallback**: `gpt-5.5` (triggered only on specific failure modes: tool errors, user-visible corrections, or complex multi-file refactoring).
3. **Balanced Fallback ("Guinevere Combo")**: Route to Tier 2 cheap providers (GLM/MiniMax) when GPT-5.5 quota is exhausted, before falling back to free Tier 3 providers.

---

## 7. Next Actions
- [ ] Configure 9Router `localhost:20128` with DeepSeek V4 Flash as Tier 1 and GPT-5.5 as Tier 2.
- [ ] Implement RTK Token Saver in the proxy chain to validate the 20-40% input reduction claim.
- [ ] Draft `k6` or `LLMPerf` script using the Phase 3 concurrency sweep methodology.
- [ ] Execute a 4-hour soak test at 80% capacity before finalizing Phase 6 migration.
