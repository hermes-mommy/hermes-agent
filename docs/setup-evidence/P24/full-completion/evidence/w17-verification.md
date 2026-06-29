# W17 Verification — M17 Production Pass (Group F start)

> **Date**: 2026-06-29
> **Wave**: W17 (final module wave)
> **Verdict**: PASS

---

## Files Created

| # | File | Lines | Purpose |
|---|------|-------|---------|
| 1 | `guinevere/production/__init__.py` | ~45 | Re-exports CircuitBreakerSet, BreakerState, TailscaleHardener, AutoRecovery, wire |
| 2 | `guinevere/production/circuit_breakers.py` | ~910 | 6 circuit breakers + CircuitBreakerSet orchestrator + Prometheus metrics |
| 3 | `guinevere/production/tailscale.py` | ~175 | TailscaleHardener: generates hardening script (D2 local-only, NOT executed) |
| 4 | `guinevere/production/recovery.py` | ~165 | AutoRecovery: systemd unit generation + signal handlers + wire(agent) |
| 5 | `tests/p24/test_circuit_breakers.py` | ~580 | 58 tests: all 6 breakers, state transitions, dream cap, subagent cap |

---

## 6 Circuit Breakers — All 3 States Verified

| # | Breaker | Threshold | CLOSED | OPEN | HALF_OPEN |
|---|---------|-----------|--------|------|-----------|
| B1 | CostExplosionBreaker | $5.00/session (configurable) | cost < threshold | cost >= threshold | after reset_timeout |
| B2 | InfiniteLoopBreaker | 3 consecutive SHA-256 fingerprints | unique calls | 3+ identical | after 60s timeout |
| B3 | HallucinationSpiralBreaker | 5% grounding ratio over 20-turn window | ratio >= 5% | ratio < 5% | after 300s timeout |
| B4 | EmotionalFixationBreaker | 10 consecutive same emotion | diverse emotions | 10+ same | after 120s timeout |
| B5 | DreamFloodingBreaker | 5 dreams/hour | < 5 dreams | >= 5 dreams | after 1800s timeout |
| B6 | SubAgentExplosionBreaker | 10 concurrent / 50 total | within caps | at cap | after 60s timeout |

Each breaker tested for:
- Starts in CLOSED
- Trips to OPEN on threshold
- OPEN blocks requests
- Transitions to HALF_OPEN on timeout
- HALF_OPEN allows probe
- Success returns to CLOSED

---

## Verification Commands — Actual Output

```bash
$ python -c "from guinevere.production import CircuitBreakerSet, BreakerState; print('OK')"
OK

$ python -c "from guinevere.production.circuit_breakers import CircuitBreakerSet; s=CircuitBreakerSet(); print('breakers:', len(s.breakers), sorted(s.breakers.keys()))"
breakers: 6 ['cost_explosion', 'dream_flooding', 'emotional_fixation', 'hallucination_spiral', 'infinite_loop', 'sub_agent_explosion']

$ python -c "from guinevere.production.circuit_breakers import BreakerState; print('states:', [s.name for s in BreakerState])"
states: ['CLOSED', 'OPEN', 'HALF_OPEN']

$ pytest tests/p24/test_circuit_breakers.py -q
58 passed in 2.33s

$ python -c "from guinevere.production.tailscale import TailscaleHardener; t=TailscaleHardener(); print('script generated:', len(t.generate_hardening_script())>0)"
script generated: True

$ grep -rn '# type: ignore\|bare except\|hard_stop\|safe_mode\|consent_gate' guinevere/production/
(exit code 1 — 0 matches)
```

---

## D2 Compliance

- **Tailscale**: Script generated but NOT executed. Exits early when `P24_ENVIRONMENT != production`.
- **AutoRecovery**: Systemd unit generated but NOT installed. Design-only under D2.
- **Tests**: All mocked, no real VPS deployment.

---

## Prometheus Metrics

Registered in `circuit_breakers.py` (fail-soft if prometheus_client not installed):

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `guinevere_m17_breaker_state` | Gauge | `breaker_name` | 0=closed, 1=open, 2=half_open |
| `guinevere_m17_breaker_trips_total` | Counter | `breaker_name` | Total breaker trips |
| `guinevere_m17_cost_usd_total` | Gauge | — | Cumulative cost this session |
| `guinevere_m17_grounding_ratio` | Gauge | — | Current memory grounding ratio |
| `guinevere_m17_emotion_consecutive` | Gauge | — | Consecutive turns with same emotion |
| `guinevere_m17_dreams_this_hour` | Gauge | — | Dreams in current hour window |
| `guinevere_m17_subagents_active` | Gauge | — | Currently active sub-agents |
| `guinevere_m17_subagents_total` | Counter | — | Total sub-agents spawned |
| `guinevere_m17_recovery_restarts_total` | Counter | — | Auto-recovery restarts |

---

## Patterns Ported

| Source | Pattern | Target |
|--------|---------|--------|
| `src/loops/circuit_breaker.py:37-43` | CircuitState enum (CLOSED/OPEN/HALF_OPEN) | `BreakerState` enum |
| `src/loops/circuit_breaker.py:83-207` | DependencyCircuitBreaker state machine | `CircuitBreaker` base class |
| `src/loops/circuit_breaker.py:245-249` | SHA-256 fingerprint | `InfiniteLoopBreaker._fingerprint()` |
| `src/x_poster/circuit_breaker.py` | allow_request/record_success/record_failure | All 6 breakers |
| `src/loops/budget.py:31` | $5.00 default cost cap | `CostExplosionBreaker` threshold |
| `src/loops/concurrency.py:58` | Semaphore pattern | `SubAgentExplosionBreaker` |
| `src/x_poster/metrics.py` | Prometheus Counter/Gauge/Counter | M17 metric families |

---

## Footer

W17 is the final module wave of P24 v3.0. All 6 circuit breakers implement the full 3-state CLOSED/OPEN/HALF_OPEN machine. Tailscale hardening is generated but not executed (D2). Auto-recovery is design-only (D2). 58 tests pass with 0 failures. No forbidden patterns detected.

**No blockers. W17 PASS.**
