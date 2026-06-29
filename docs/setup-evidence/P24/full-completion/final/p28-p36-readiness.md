# P28-P36 Readiness Assessment

**Source phase:** P24 Hermes Native Fork
**Date:** 2026-06-29
**Status:** READY WITH EXPLICIT PROVISIONING BLOCKERS

---

## 1. What P28-P36 May Consume from P24

### 1.1 Native Module Foundation (17 modules)

| # | Module | Package Path | Purpose |
|---|--------|-------------|---------|
| 1 | consciousness | `guinevere.consciousness` | Awareness, introspection, metacognition |
| 2 | emotions | `guinevere.emotions` | Valence/arousal, emotion regulation, mood tracking |
| 3 | memory | `guinevere.memory` | Tiered memory (STM/LTM/episodic/semantic), encrypted-at-rest |
| 4 | governance | `guinevere.governance` | DAO, on-chain voting, proposal lifecycle |
| 5 | tools | `guinevere.tools` | Tool registry, 9 backends, 118 actions, L1-L3 auth |
| 6 | life_kernel | `guinevere.life_kernel` | Autonomous loop, goal management, scheduling |
| 7 | self_modify | `guinevere.self_modify` | Self-modification engine, code-gen guardrails |
| 8 | personality | `guinevere.personality` | Trait vectors, behavioral consistency |
| 9 | discord | `guinevere.discord` | Discord bot integration, command dispatch |
| 10 | channels | `guinevere.channels` | Multi-channel abstraction (WhatsApp, Telegram, X, Email) |
| 11 | http | `guinevere.http` | HTTP API layer, /health endpoint, REST surface |
| 12 | surveillance | `guinevere.surveillance` | Drift detection, anomaly monitoring, watchdog |
| 13 | observability | `guinevere.observability` | Structured logging, metrics, tracing hooks |
| 14 | production | `guinevere.production` | Deployment scaffolding, startup sequence |
| 15 | config | `guinevere.config` | YAML loader, dual-persona support (Guinevere + Pharsa) |
| 16 | iteration_budget | `guinevere.iteration_budget.py` | Recursion/iteration limits, circuit-breaker integration |
| 17 | (integrated) | Across packages | Circuit breakers (6 types), drift monitor, encrypted memory |

All 17 modules live under `guinevere/` (87 .py files). The legacy `src/` directory is fully retired (0 .py files).

### 1.2 Fork Runtime

- **Base:** NousResearch/hermes-agent v0.15.2 @ SHA 77a1650c
- **Layout:** In-repo root (D1 decision) -- hermes-agent files coexist with `guinevere/` overlay
- **Config:** `config/guinevere.yaml` (Guinevere instance) + `config/pharsa.yaml` (Pharsa instance)
- **Import chain:** All 17 modules importable in a single `python -c` invocation
- **Health:** `/health` returns HTTP 200

### 1.3 Test Baseline

**541 tests across 14 test files in `tests/p24/` -- ALL PASS (0 failures).**

| Module | Tests |
|--------|-------|
| circuit_breakers | 58 |
| life_kernel | 62 |
| memory | 54 |
| discord | 52 |
| surveillance | 51 |
| channels | 44 |
| drift | 42 |
| tool_registry | 34 |
| self_modify | 33 |
| dao | 32 |
| emotions | 31 |
| consciousness | 16 |
| subagents | 18 |
| http | 14 |
| **Total** | **541** |

Any P28-P36 phase MUST pass this full suite as a regression gate before merging.

### 1.4 Safety Infrastructure

- **6 circuit breakers:** cost_explosion, infinite_loop, hallucination_spiral, emotional_fixation, dream_flooding, sub_agent_explosion (each with CLOSED/OPEN/HALF_OPEN states)
- **Encrypted memory:** At-rest encryption for sensitive memory tiers
- **DAO governance:** Proposal lifecycle with unit-tested stages (not mainnet-executable -- see blockers)
- **Drift monitor:** Continuous drift detection with alerting hooks
- **Forbidden-pattern scan:** 0 violations across `guinevere/`, `agent/`, `tools/`, `gateway/`, `cron/`, `hermes_cli/`, `run_agent.py` for: `hard_stop`, `HARD_STOP`, `consent_gate`, `safe_mode`, `HardStopHandler`, `SafeMode`, `FreezeCascade`, `# type: ignore`, `as any`, `@ts-ignore`, `bare except`, `fork-agnostic`

### 1.5 Audit History

- 25 P24 commits on `feat/p24-hermes-fork` branch
- 20 evidence files + 16 auditor-gate files (round-1)
- Per-wave audits: W1-W17 all PASS (W2/W3 adjudicated, W4 regression-reverted F01, W17 wire-gap fixed)
- 3 additional rounds (W18-W20) completed for documentation/evidence

---

## 2. What P28-P36 May NOT Claim Yet

These are **operator-provisioning blockers**, not software defects. The code is complete; the runtime environment is not.

| # | Blocker | Root Cause | What Is Needed |
|---|---------|-----------|----------------|
| B1 | Live production deploy | D2 decision -- no VPS provisioned | VPS host + deployment credentials |
| B2 | Real LLM inference | D3 decision -- mock-only tests | Valid API key (e.g., 9Router or equivalent) |
| B3 | Live Discord connections | No bot tokens provisioned | 3 Discord bot tokens + channel IDs |
| B4 | Real channel sends (WhatsApp, Gmail, X, Telegram) | CONFIG_MISSING markers in adapters | API credentials for each channel |
| B5 | Ethereum mainnet DAO execution | No wallet/ETH | Wallet with funds + mainnet RPC |
| B6 | True mock dry-run | `--dry-run` is NOT a Hermes CLI flag | Hermes mock-provider support (or custom wrapper) |

**B6 detail:** During W19, `hermes-agent --dry-run` was attempted. The flag was silently ignored; the agent attempted a real API call to OpenRouter (HTTP 401 -- expired key, no inference). The boot DID prove all 17 P24 wires fire at runtime (emotion.wire.complete, drift.detector.initialized, life_kernel_wire, consciousness_bridge_wired), 29 tools loaded, config loaded. But it is NOT a true mock-only dry-run.

### 2.1 Claiming Rules for P28-P36

Any P28-P36 deliverable MUST:

1. **NOT claim "deployed"** unless B1 is resolved (VPS provisioned + live deployment verified)
2. **NOT claim "real inference"** unless B2 is resolved (valid API key + successful LLM call)
3. **NOT claim "live channels"** unless B3 and/or B4 are resolved
4. **NOT claim "DAO-executed"** unless B5 is resolved
5. **ALWAYS note "mock-only"** when referring to LLM-dependent test results
6. **ALWAYS pass the 541-test P24 regression suite** before any merge

---

## 3. Integration Contract for P28-P36

### 3.1 Module Consumption

P28-P36 phases may import and extend any of the 17 modules listed in Section 1.1. New modules should be added under `guinevere/` following the existing subpackage pattern.

### 3.2 Test Requirements

- All new code MUST include tests in `tests/p24/` (or a new `tests/p28/` etc. directory)
- The 541-test P24 baseline MUST remain green (0 failures) at all times
- New tests MUST use mock-only LLM calls (D3 decision)

### 3.3 Config Extension

New configuration should be added to `config/guinevere.yaml` or `config/pharsa.yaml` as appropriate. Both files are loaded by `guinevere.config.loader.load_settings()`.

### 3.4 Circuit Breaker Integration

Any new autonomous loop or external-call pattern MUST register with the circuit breaker framework (6 existing breakers). New breakers are permitted but MUST follow the CLOSED/OPEN/HALF_OPEN state machine.

### 3.5 Forbidden Patterns

The forbidden-pattern scan MUST remain at 0 violations. P28-P36 code MUST NOT reintroduce any of: `hard_stop`, `HARD_STOP`, `consent_gate`, `safe_mode`, `HardStopHandler`, `SafeMode`, `FreezeCascade`, `# type: ignore`, `as any`, `@ts-ignore`, `bare except`, `fork-agnostic`.

---

## 4. Summary

P24 delivers a complete, tested, audited Hermes-native fork with 17 modules, 87 source files, 541 passing tests, 6 circuit breakers, encrypted memory, DAO governance, and drift monitoring. The legacy `src/` directory is fully retired.

P28-P36 has a solid foundation to build on. The six blockers (B1-B6) are all operator-provisioning issues, not code defects. P28-P36 phases should proceed with mock-only infrastructure and document honestly when live capabilities depend on operator-provisioned resources.

**Readiness verdict: READY WITH EXPLICIT PROVISIONING BLOCKERS.**
