# P20 Continuation — Evidence Consistency Research Report

**Date:** 2026-06-24
**Agent role:** evidence/docs consistency researcher
**Scope:** Reconcile claims made in P20 documentation against actual code, test output, and the orchestrator-provided authoritative context. Identify every doc that over-claims or under-claims, and list required doc updates for Phase 9 finalization.

---

## 1. Executive Summary

The P20 Living Autonomy Kernel is functionally **online and visibly autonomous on Discord** (Option-B core-integrated REST publisher), but it is **NOT yet at "PRODUCTION PASS"**. The 24h clean soak is incomplete and several critical implementation gaps remain (P16/P18 adapter stubs, random idle_node, missing journal system, placeholder heartbeat 10s/5m/1h loops, unwired session graph).

**Most importantly, the documented test count is stale.** Several reports claim `390 passed, 7 skipped, 0 failed`. The actual local run on 2026-06-24 produced **397 passed, 7 skipped, 0 failed**. This means the docs under-count by 7 tests and incorrectly imply the suite is static.

This report details which documents over-claim production pass, which under-claim progress, and what must be updated as part of Phase 9 finalization.

---

## 2. Current State Evidence (file:line citations)

### 2.1 Discord-visible autonomy is implemented

`src/core/main.py:284-296` constructs the `DashboardWriter`, `DiscordLogChannel`, and `HeartbeatService`:

```python
# src/core/main.py:284-296 (representative)
dashboard_writer = DashboardWriter(...)
log_channel = DiscordLogChannel(...)
heartbeat = HeartbeatService(
    graph=graph, redis_client=redis_client, checkpointer=checkpointer,
    discord_publisher=dashboard_writer, hermes_brain=hermes_brain,
    log_channel=log_channel,
)
```

`src/life_kernel/heartbeat.py:460-482` invokes the graph every 60s and publishes dashboard + log:

```python
# src/life_kernel/heartbeat.py:460-482
result = await self.graph.ainvoke(...)
if self._discord_publisher is not None:
    await self._discord_publisher.update_dashboard(state)
await self._log_lifecycle_milestone(state)
```

`src/life_kernel/dashboard.py:216` uses a SHA-256 checksum to skip redundant renders (edit-not-spam).

### 2.2 HARD STOP safety and recovery are implemented

`src/life_kernel/heartbeat.py:254-324` checks Redis `life_kernel:hard_stop` every second, sets `hard_stop_requested=True` in graph state, publishes to Discord, writes to log, and stops all heartbeat tasks.

`src/life_kernel/heartbeat.py:326-350` recovers from stale checkpoint state when the Redis flag is absent — this is the fix for the stuck-HARD-STOP bug.

`src/life_kernel/graph.py:211-213` routes HARD STOP to END non-LLM:

```python
if state.get("hard_stop_requested", False):
    logger.warning("HARD_STOP requested - routing to END")
    return {"decision": "end"}
```

### 2.3 Test count mismatch

Command run from repo root on 2026-06-24:

```bash
python -m pytest tests/life_kernel/ -q --disable-warnings --tb=no 2>&1 | tail -5
```

Actual output:

```text
397 passed, 7 skipped, 2173 warnings in 113.28s (0:01:53)
```

This contradicts every document that still reports `390 passed, 7 skipped, 0 failed`.

### 2.4 Critical implementation gaps remain (placeholders confirmed)

`src/life_kernel/graph.py:129` has the explicit placeholder:

```python
world_model_available = False  # Placeholder for P18 integration
```

`src/life_kernel/graph.py:463-468` uses `random.choice` over hardcoded idle strings:

```python
task_options = [
    ("exploration", "Exploration: review life_kernel state for patterns"),
    ("self_improvement", "Self-improvement: evaluate SDLC loop efficiency"),
    ("learning", "Learning: revisit recent observations for insights"),
]
task_type, task_description = random.choice(task_options)
```

`src/life_kernel/p16_adapter.py:39-99` and `src/life_kernel/p18_adapter.py:40-102` return mock data with `"_placeholder": True`.

`src/life_kernel/heartbeat.py:373-571` confirms 10s/5m/1h heartbeat loops are stubs with only debug logging and "Placeholder for future" comments.

### 2.5 P16/P18 decision_context is never built with real substrates

`src/life_kernel/graph.py:159-170` checks `kg_adapter` and `memory_adapter` from state but falls back to unavailable because these adapters are never injected. `src/core/main.py:204-296` creates the graph and heartbeat but never sets `kg_adapter` or `memory_adapter` on initial state.

Real substrates exist but are unused by the life kernel:
- `src/knowledge_graph/query/engine.py` — `KGQueryEngine`
- `src/knowledge_graph/query/context.py` — `RecallContextAssembler`
- `src/knowledge_graph/query/rrf_fusion.py` — `KGRRFFusion`
- `src/memory/read_pipeline.py` — `async recall_memories(...)`

---

## 3. Reconciliation Table: Claim vs. Actual Truth

| Claim | Document Location | Actual Truth | Required Doc Update |
|---|---|---|---|
| Status: **PRODUCTION STABILIZED — SOAK IN PROGRESS — PRODUCTION PASS HOLD** | `docs/setup-evidence/P20/evidence/production-stabilization/final-stabilization-report.md:1`, `:8`, `:17` | Correctly conservative; matches authoritative context that 24h soak is incomplete | None — this is the correct status |
| Status: **PRODUCTION DEPLOYED — SOAK IN PROGRESS — PRODUCTION PASS HOLD** | `docs/setup-evidence/P20/evidence/production-rollout/final-production-rollout-report.md:1`, `:8`, `:17` | Correctly conservative; matches authoritative context | None |
| Status: **VISIBLE AUTONOMY ONLINE — SOAK IN PROGRESS — P20 PASS HOLD** | `docs/setup-evidence/P20/evidence/discord-visible-autonomy/final-discord-visible-autonomy-report.md:4`, `:80` | Correctly conservative; explicitly says "NOT P20 PRODUCTION PASS" | None |
| Test count: **390 passed, 7 skipped, 0 failed** | `docs/setup-evidence/P20/README.md:84`, `evidence/LK-017/verification.md:37`, `evidence/LK-017/verification.md:140`, `evidence/LK-017/auditor-gate.md:52`, `evidence/LK-017/auditor-gate.md:74`, `evidence/production-stabilization/final-stabilization-report.md:10`, `evidence/production-stabilization/final-stabilization-report.md:77`, `evidence/production-rollout/final-production-rollout-report.md:9`, `evidence/production-rollout/final-production-rollout-report.md:67` | **397 passed, 7 skipped, 0 failed** as of 2026-06-24 | Update all listed docs to 397 passed |
| LK-017 verdict: **LOCAL STAGED PASS — PRODUCTION ROLLOUT HOLD** | `docs/setup-evidence/P20/evidence/LK-017/auditor-gate.md:9`, `:72` | Correctly conservative; no production rollout claimed | None |
| P20 is "PRODUCTION PASS" or "COMPLETE" | Not found in any read doc | Not true; all reports correctly say PASS HOLD | Continue to reject any such claim |
| 24h clean soak complete | None of the read docs claim this | Not complete per authoritative context | N/A |
| Discord-visible autonomy online with dashboard `1519135545501028549` | `final-discord-visible-autonomy-report.md:39` | Authoritative context confirms dashboard + log are live; dashboard ID matches | None |
| `world_model_available = False` is only a placeholder | This report confirms it from `graph.py:129` | True; P18 integration is not wired | Document in continuation gap table |
| idle_node uses random hardcoded strings | This report confirms from `graph.py:463-468` | True; AC-LIFE-002 fails | Document in continuation gap table |
| p16_adapter and p18_adapter are stubs | This report confirms from code | True; real KG/memory substrates untouched | Document in continuation gap table |
| heartbeat 10s/5m/1h are placeholders | This report confirms from `heartbeat.py:373-571` | True | Document in continuation gap table |

---

## 4. Gap Table

| ID | Severity | Title | Current State | Required State | Files | Vision Ref |
|---|---|---|---|---|---|---|
| gap-docs-test-count | medium | Documented test count is stale (390 vs 397) | Multiple P20 evidence docs still claim `390 passed, 7 skipped, 0 failed` | Update to `397 passed, 7 skipped, 0 failed` and add timestamp | `docs/setup-evidence/P20/README.md:84`; `evidence/LK-017/verification.md:37,140`; `evidence/LK-017/auditor-gate.md:52,74`; `evidence/production-stabilization/final-stabilization-report.md:10,77`; `evidence/production-rollout/final-production-rollout-report.md:9,67` | Phase 9 finalization |
| gap-world-model-placeholder | critical | `world_model_available` hardcoded to False | `graph.py:129` sets `world_model_available = False` | Query real world-model state from P18 memory / P16 KG | `src/life_kernel/graph.py:129` | V-001, AC-LIFE-005 |
| gap-idle-random | critical | idle_node is random, not world-state-driven | `graph.py:463-468` uses `random.choice` over 3 hardcoded strings | Self-directed task seeded by P18 recall + world-state | `src/life_kernel/graph.py` | V-003, AC-LIFE-002 |
| gap-p16-p18-stubs | critical | KG/memory adapters return mock data | `p16_adapter.py:39-99`, `p18_adapter.py:40-102` return `_placeholder: True` | Call real `KGQueryEngine` / `RecallContextAssembler` / `recall_memories` | `src/life_kernel/p16_adapter.py`, `src/life_kernel/p18_adapter.py`, `src/core/main.py`, `src/life_kernel/graph.py:159-170` | AC-LIFE-005 |
| gap-journal | high | No internal journal system | `LifeMindState` lacks `journal_entries`; `reflect_node` only writes audit metadata | Add `journal_entries` and write reflective entries after meaningful cycles | `src/life_kernel/state.py`, `src/life_kernel/graph.py` | V-001, AC-LIFE-008 |
| gap-self-improvement | high | Self-improvement is placeholder | `self_improve.py` generators return hardcoded strings; `_heartbeat_1h` is stub | Wire `ReflectionEvaluator` into 1h heartbeat and generate Hermes-driven candidates | `src/life_kernel/self_improve.py`, `src/life_kernel/heartbeat.py:551` | AC-LIFE-009 |
| gap-session-graph | high | SDLC session graph is not wired | `session_graph.py` exists but is never invoked from `idle_node`/`act_node` | Spawn session graph for self-created SDLC tasks | `src/life_kernel/session_graph.py`, `src/life_kernel/graph.py` | AC-LIFE-003 |
| gap-heartbeat-stubs | medium | 10s/5m/1h heartbeat loops are placeholders | `heartbeat.py:373-571` only log debug messages | Implement stuck detection (10s), deep scan (5m), reflection (1h) | `src/life_kernel/heartbeat.py` | Benchmark sections 9.2, 9.4 |
| gap-sensor-adapters | medium | `sensor_adapters.py` module missing | `src/life_kernel/__init__.py` imports from `sensor_adapters` but file does not exist | Create `sensor_adapters.py` or remove imports | `src/life_kernel/__init__.py`, `src/life_kernel/sensor_adapters.py` (new) | LK-011 |

---

## 5. Risks

| Risk | Mitigation |
|---|---|
| Stale test count in evidence undermines audit credibility | Update every listed doc to `397 passed` and date-stamp the run |
| Placeholder P16/P18 adapters mean autonomy decisions are not memory-backed | Prioritize wiring real `KGQueryEngine` and `recall_memories` in the continuation implementation pass |
| Random idle_node makes autonomy appear shallow | Inject P18 recall context and world-state summary into `_make_brain_idle`; keep random only as brain-fallback |
| Missing journal blocks AC-LIFE-008 | Add `journal_entries` to state and write from `reflect_node` before claiming completion |
| Heartbeat 10s/5m/1h stubs leave 2 of 3 deep-cognition cycles unimplemented | Implement at minimum stuck detection (10s) and reflection (1h) before Phase 9 sign-off |
| Phase 9 finalization may over-claim if not reconciled | Use this report as the canonical truth source; no doc may claim PRODUCTION PASS until 24h soak + gap closure |

---

## 6. Hard-Rejection Flags

| Flag | Status | Evidence |
|---|---|---|
| Raw `LLMRouter.chat` used as brain path | Clear | `hermes_brain.py` uses `AIAgent.run_conversation()`; graph uses `_safe_think()` wrapping `hermes_brain.think()` |
| HARD STOP weakened or removed | Clear | Non-LLM route to END in `graph.py:211-213`; Redis check every 1s in `heartbeat.py:254-324` |
| "heartbeat" terminology replaced with user-facing "pulse" | Clear | "heartbeat" used consistently throughout code and docs |
| Secrets in output | Clear | No secrets observed in evidence or code |
| Display-only autonomy violated | Clear | All graph actions are display-only per operator approval and docs |

No hard-rejection flags are currently active.

---

## 7. Concrete Recommendation for Implementation Phase

### Phase 9 documentation updates (do first)

1. **Update test count** in all listed documents to `397 passed, 7 skipped, 0 failed` and add the run date (2026-06-24).
2. **Add a P20 continuation status note** to `docs/setup-evidence/P20/README.md` linking to this evidence-consistency report and the gap-auditor report.
3. **Reconcile `final-status-consistency.md`** with the new test count and current PASS HOLD status.

### Implementation priorities for continuation

1. **P16/P18 integration (critical)**: Replace `p16_adapter.py` and `p18_adapter.py` stubs with real calls; inject adapters in `src/core/main.py`.
2. **World-model availability (critical)**: Remove `world_model_available = False` placeholder and derive from real state.
3. **World-state-driven idle (critical)**: Use P18 recall + observations to seed idle tasks instead of `random.choice`.
4. **Journal system (high)**: Add `journal_entries` to `LifeMindState`; write reflective entries in `reflect_node`.
5. **Self-improvement wiring (high)**: Implement `_heartbeat_1h` using `ReflectionEvaluator`.
6. **Session graph wiring (high)**: Spawn `session_graph.py` from `act_node` for SDLC-type tasks.
7. **Heartbeat stubs (medium)**: Implement 10s stuck-detection and 1h reflection loops.
8. **sensor_adapters.py (medium)**: Create the missing module or clean up `__init__.py` imports.

### Docs that MUST be updated as part of Phase 9 finalization

- `docs/setup-evidence/P20/README.md` — test count, status note
- `docs/setup-evidence/P20/evidence/LK-017/verification.md` — test count
- `docs/setup-evidence/P20/evidence/LK-017/auditor-gate.md` — test count
- `docs/setup-evidence/P20/evidence/LK-017/auditor-matrix.md` — test count if present
- `docs/setup-evidence/P20/evidence/production-stabilization/final-stabilization-report.md` — test count
- `docs/setup-evidence/P20/evidence/production-rollout/final-production-rollout-report.md` — test count
- `docs/setup-evidence/P20/evidence/final-status-consistency.md` — reconcile with actual truth
- `PROGRESS.md` — P20 status should remain "HOLD / 24h soak pending"
- `CHECKLIST.md` — P20 checklist should reflect HOLD and link to continuation evidence

---

## 8. Footer

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-24 | Evidence consistency researcher | Initial reconciliation report for P20 continuation pass |
