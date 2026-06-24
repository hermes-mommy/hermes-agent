# P20 Living Autonomy Kernel — Continuation Plan

| Field | Value |
|---|---|
| Status | PLAN READY — implementation authority for the P20 Living Autonomy completion pass |
| Date | 2026-06-24 |
| Owner | Faiz (authoritative correction) |
| Executor | Guinevere (full autonomous workflow) |
| Evidence root | `docs/setup-evidence/P20/evidence/continuation/` |
| Research input | `docs/setup-evidence/P20/evidence/continuation/research/*.md` (7 specialist reports, 59 gaps) |
| Runtime target | Production Guinevere on `guinevere-vps` (Tailscale 100.94.104.22) |
| Baseline tests | 397 passed, 7 skipped, 0 failed (2026-06-24 12:35 WIB) |

## 0. Executive Summary

The P20 Living Autonomy Kernel has a **solid architectural skeleton** — LangGraph 4-node graph, 6-interval heartbeat, HermesBrain bridge (`model=guinevere`, zero fallback), Discord REST dashboard+log (LIVE, edit-not-spam), PostgreSQL models, and a correct non-LLM HARD STOP. The stuck-HARD-STOP bug and HermesBrain AIAgent TypeError are **already fixed and live**.

However, **7 of 10 AC-LIFE success criteria are PARTIAL/PLACEHOLDER/FAIL**. The kernel boots and cycles and publishes, but it is **not genuinely living/autonomous**:

- **AC-LIFE-002 FAIL**: `idle_node` uses `random.choice` over 3 hardcoded strings — not world-state-driven.
- **AC-LIFE-005 FAIL**: `p16_adapter`/`p18_adapter` are stubs returning mock data; adapters are **never injected** into graph state, so `decision_context` is never built from real substrates despite production-grade `RecallContextAssembler` and `recall_memories` existing.
- **AC-LIFE-008 FAIL**: No journal system; `reflect_node` writes audit metadata only.
- **AC-LIFE-009 FAIL**: `ReflectionEvaluator` is coded but **never called**; generators return hardcoded strings.

This continuation implements the real gaps: wire P16/P18 into observe/decide/idle, make idle memory-driven, add journals, wire self-improvement, and resolve the empty-state trap. **Display-only autonomy v1** (agenda + dashboard + log, no DMs/side-effects) per operator approval.

## 1. Gap Matrix (against original plan)

| Gap ID | Severity | AC/Vision | Current State (file:line) | Required State | Files |
|---|---|---|---|---|---|
| GAP-WORLD-MODEL | **critical** | V-001, AC-LIFE-005 | `graph.py:129` hardcodes `world_model_available = False` | Compute from real adapter availability; set `world_model_status` | `graph.py`, `state.py` |
| GAP-P16-STUB | **critical** | AC-LIFE-005, LK-010 | `p16_adapter.py:63-99` returns mock concepts `_placeholder:True` | Wrap real `RecallContextAssembler.assemble()`; degrade gracefully | `p16_adapter.py` |
| GAP-P18-STUB | **critical** | AC-LIFE-005, LK-010 | `p18_adapter.py:66-102` returns mock memories `_placeholder:True` | Wrap real `recall_memories()`; degrade gracefully | `p18_adapter.py` |
| GAP-ADAPTER-INJECTION | **critical** | LK-010, BD-005 | `graph.py:160-170` reads `state.get('kg_adapter')` always None; `main.py` never injects | Inject real adapters at `create_life_mind_graph()` from `main.py` lifespan | `graph.py`, `core/main.py` |
| GAP-EMPTY-STATE-TRAP | **critical** | AC-LIFE-002 | `decide_node` routes to `idle` when goals/commitments/concerns all empty (`graph.py:240-242`); brain never seeds goals | When idle + memory available, generate a real goal from recall context | `graph.py` |
| GAP-IDLE-RANDOM | **critical** | V-003, AC-LIFE-002 | `idle_node` `random.choice` over 3 hardcoded strings (`graph.py:463-468`) | Memory-driven agenda; brain proposes context-driven task seeded by recall | `graph.py` |
| GAP-DISPLAY-ONLY-IDLE | **critical** | AC-LIFE-002 | `brain_idle` enriches description only, never creates a real goal (`graph.py:614-636`) | Brain-generated task creates a real goal/commitment in `state.goals[]` | `graph.py` |
| GAP-JOURNAL | **high** | V-001, AC-LIFE-008 | No `journal_entries` field; `reflect_node` audit metadata only (`graph.py:388-432`) | Add `journal_entries`; write reflective entries after meaningful cycles | `state.py`, `graph.py`, `journal.py` |
| GAP-SELF-IMPROVE-WIRING | **high** | AC-LIFE-009 | `ReflectionEvaluator` coded but never called; `_heartbeat_1h` is stub (`heartbeat.py:551`) | Wire `ReflectionEvaluator` into 1h heartbeat; HermesBrain candidates | `self_improve.py`, `heartbeat.py` |
| GAP-BRAIN-FEED | **high** | AC-LIFE-005 | Brain prompts lack recall context (`graph.py:548-552`) | Inject `recalled_concepts`/`recalled_memories` into decide/act/idle prompts | `graph.py` |
| GAP-MEMORY-STATUS-DASH | **high** | V-003, LK-010 | Dashboard Memory field always `—`; no node writes `memory_status` | A node writes concise recall summary to `memory_status` | `graph.py`, `dashboard.py` |
| GAP-CURRENT-FOCUS | **medium** | V-003 | `current_focus` never populated; dashboard shows `—` | Decide/act sets `current_focus` to active goal/domain | `graph.py` |
| GAP-LOG-NARRATIVE | **medium** | V-003 | Log line is raw counters (`heartbeat.py:494-528`) | Include one-sentence autonomous intent | `heartbeat.py` |
| GAP-HEARTBEAT-STUBS | **medium** | §9.2, §9.4 | `_heartbeat_10s/30s/5m/1h` are debug-log stubs (`heartbeat.py:373-571`) | Implement stuck-detection (10s), reflection batch (1h) | `heartbeat.py` |
| GAP-DOCS-TEST-COUNT | **medium** | Phase 9 | Docs claim `390 passed`; actual `397 passed` | Update all docs to `397 passed, 7 skipped` | multiple docs |

**Resolved / Not-actioned (already live, per research):**
- Stuck-HARD-STOP: FIXED (`_heartbeat_1s` recovery clears stale checkpoint).
- HermesBrain TypeError: FIXED (`_default_agent_factory`).
- Discord REST publisher: LIVE (edit-not-spam, Redis message-id persistence).
- `guinevere-discord.service`: intentionally MASKED (Option B core REST publisher is the writer).
- `sensor_adapters.py`: the gap-auditor flagged it missing but it exists as a **package dir** (`src/life_kernel/sensor_adapters/`); `__init__.py` imports correctly. NOT a hard-rejection bug — verified by `397 passed` import working.

## 2. Exact Todo List

| Todo | Title | Depends On | Wave |
|---|---|---|---|
| T1 | Extend `LifeMindState` with journal + recall fields | — | 1 |
| T2 | Create `JournalWriter` wrapping PostgresAuditJournal | T1 | 1 |
| T3 | Create `adapter_factory` (real KG/memory adapter construction) | — | 1 |
| T4 | Rewrite `p16_adapter.recall` to use real RecallContextAssembler | T3 | 2 |
| T5 | Rewrite `p18_adapter.recall` to use real recall_memories | T3 | 2 |
| T6 | Inject adapters into graph + wire observe_node to build real decision_context | T1,T4,T5 | 3 |
| T7 | Fix empty-state trap: decide_node seeds goal from memory when idle | T6 | 3 |
| T8 | Memory-driven idle_node: replace random.choice with recall-seeded brain proposal that creates a real goal | T6,T7 | 3 |
| T9 | Feed recalled context into decide/act/idle brain prompts | T6 | 3 |
| T10 | Wire journal writes into reflect_node + set `memory_status`/`current_focus` | T2,T6 | 3 |
| T11 | Wire `ReflectionEvaluator` into `_heartbeat_1h` (self-improvement candidates) | T10 | 4 |
| T12 | Enrich lifecycle log line with autonomous intent narrative | T10 | 4 |
| T13 | Full test suite green + audit wave 1 | T1-T12 | 5 |
| T14 | Deploy to VPS (scp, restart core only, smoke, verify others undisturbed) | T13 | 6 |
| T15 | Runtime verification + Discord proof + docs/evidence + final report | T14 | 7 |

## 3. Dependency Map

```text
Wave 1 (parallel):
  T1 state fields ─────┐
  T2 JournalWriter ◄── T1
  T3 adapter_factory ──┤
                       │
Wave 2 (parallel):     │
  T4 p16 real ◄── T3   │
  T5 p18 real ◄── T3   │
                       │
Wave 3 (sequential):   │
  T6 inject+observe ◄── T1,T4,T5
  T7 empty-state trap ◄── T6
  T8 memory-driven idle ◄── T6,T7
  T9 brain prompt feed ◄── T6
  T10 journal+memory_status ◄── T2,T6
                       │
Wave 4 (parallel):     │
  T11 self-improve 1h ◄── T10
  T12 log narrative ◄── T10
                       │
Wave 5: T13 tests+audit1 ◄── T1-T12
Wave 6: T14 deploy ◄── T13
Wave 7: T15 verify+docs ◄── T14
```

## 4. Parallelism Map

- **Wave 1**: T1, T3 are independent (T2 depends on T1). Run T1+T3 in parallel, then T2.
- **Wave 2**: T4, T5 independent — parallel.
- **Wave 3**: T6 first (foundation), then T7/T8/T9/T10 can be parallelized (all depend on T6, touch different graph.py sections but must be sequenced to avoid merge conflicts — implement in single pass).
- **Wave 4**: T11, T12 parallel.
- All graph.py edits (T6-T10) are in one file → **sequential** in practice (one implementer).

## 5. Files to Modify

| File | Todos | Change |
|---|---|---|
| `src/life_kernel/state.py` | T1 | +`journal_entries`, `recalled_concepts`, `recalled_memories`, `world_model_status` + `add_journal_reducer` |
| `src/life_kernel/journal.py` (NEW) | T2 | `JournalWriter.write_entry()` |
| `src/life_kernel/adapter_factory.py` (NEW) | T3 | `create_kg_adapter`, `create_memory_adapter` |
| `src/life_kernel/p16_adapter.py` | T4 | real `recall()` → RecallContextAssembler |
| `src/life_kernel/p18_adapter.py` | T5 | real `recall()` → recall_memories |
| `src/life_kernel/graph.py` | T6-T10 | observe wire, empty-state fix, memory-driven idle, brain feed, journal, memory_status, current_focus |
| `src/life_kernel/self_improve.py` | T11 | real HermesBrain candidate generation |
| `src/life_kernel/heartbeat.py` | T11,T12 | `_heartbeat_1h` reflection batch; log narrative |
| `src/core/main.py` | T6 | inject adapters via adapter_factory |
| `src/life_kernel/dashboard.py` | T10 | show recalled memory/concept counts (minor) |
| Tests: `test_state_extensions.py`, `test_journal.py`, `test_adapter_factory.py`, `test_p16_adapter.py`, `test_p18_adapter.py`, `test_graph.py`, `test_decision_context.py` | T1-T12 | TDD |

## 6. Deployment Plan (policy-gated, V-003 autonomy)

1. **Predeploy scan**: `git status` clean, `python -m pytest tests/life_kernel/ -q` green locally.
2. **Backup on VPS**: `ssh guinevere-vps 'cp -r /opt/guinevere/src/life_kernel /tmp/life_kernel.bak.$(date +%s); git -C /opt/guinevere stash'` (or tag).
3. **scp changed files**: `scp src/life_kernel/*.py src/core/main.py guinevere-vps:/opt/guinevere/src/...` (only modified files).
4. **Migration**: NONE — `recall_memories` uses existing `memory.episodes` tables; no schema change.
5. **Restart ONLY core**: `ssh guinevere-vps 'sudo systemctl restart guinevere-core.service'`.
6. **Canary/smoke**: `curl /health`, `curl /health/detailed`; check `journalctl -u guinevere-core -n 50` for `kg_recall_success`/`memory_recall_success`/`journal_entry_written`/no `GraphRecursionError`/no `dashboard_publish_failed`.
7. **Verify other services undisturbed**: `systemctl is-active guinevere-mcp hermes-gateway guinevere-discord ...` all active.
8. **Discord proof**: dashboard message edited in place showing `Memory: active`, `Current Focus: <brain-generated>`, `Next Planned Action: <memory-driven>`; log channel shows narrative line.

## 7. Rollback Plan

| Scenario | Rollback |
|---|---|
| Kernel fails on startup | `ssh guinevere-vps 'git -C /opt/guinevere checkout -- .; sudo systemctl restart guinevere-core.service'` |
| GraphRecursionError | recursion_limit=25 is safe; if recurs, revert graph.py |
| Adapters crash kernel | adapters are fail-soft (`_degraded`); if still crash, set `kg_adapter=None/memory_adapter=None` in main.py (kernel runs headless, as before) |
| Dashboard publish fails | fail-soft already; kernel continues |
| HARD STOP regression | `_heartbeat_1s` recovery unchanged; test `redis SET life_kernel:hard_stop 1` → halt; `DEL` → recovery |

## 8. Verification Scaffold per Todo

| Todo | Required commands | Forbidden patterns | Hard rejection |
|---|---|---|---|
| T1 | `pytest tests/life_kernel/test_state_extensions.py -v` | `# type: ignore`, placeholder | fields missing |
| T2 | `pytest tests/life_kernel/test_journal.py -v` | empty except | crash on DB failure |
| T3 | `pytest tests/life_kernel/test_adapter_factory.py -v` | mock return | `_placeholder:True` |
| T4 | `pytest tests/life_kernel/test_p16_adapter.py -v` | hardcoded concepts | `_placeholder` with engine present |
| T5 | `pytest tests/life_kernel/test_p18_adapter.py -v` | hardcoded memories | `_placeholder` with client present |
| T6 | `pytest tests/life_kernel/test_graph.py -v`; grep `world_model_available = False` → gone | static injection | adapters not in signature |
| T7 | `pytest tests/life_kernel/test_empty_state_goal_generation.py -v` | random routing | idle when memory available |
| T8 | `pytest tests/life_kernel/test_memory_driven_idle.py -v` | `random.choice` | no goal created |
| T9 | grep brain prompts include `recalled` | missing context | brain sees no memory |
| T10 | `pytest tests/life_kernel/test_graph.py::test_reflect_journal -v` | audit-only | no journal_entries |
| T11 | `pytest tests/life_kernel/test_self_improve.py -v` | hardcoded candidates | 1h stub |
| T12 | grep log line includes intent | raw counters | no narrative |
| T13 | `pytest tests/life_kernel/ -q` ≥397 passed | skipped-to-pass | any fail |
| T14 | ssh health OK, NRestarts sane | secret in output | other services down |
| T15 | live Discord proof | docs-only | no live proof |

## 9. Auditor Matrix (waves 1 & 2)

| Auditor | Scope | Round |
|---|---|---|
| Architecture | graph topology, HermesBrain boundary, no trigger-first, empty-state fix correctness | 1 & 2 |
| Runtime | heartbeat, checkpoint, restart recovery, recursion_limit, no GraphRecursionError | 1 & 2 |
| Safety/consent | HARD STOP non-LLM, consent/DNR/classification in recall, display-only | 1 & 2 |
| Security/secrets | no tokens in logs/evidence/state, redaction, fail-soft | 1 & 2 |
| Discord UX | edit-not-spam, dashboard living state, log narrative, no spam | 1 & 2 |
| Memory/world-model | real recall wired, `_degraded` on failure, AC-LIFE-005 | 1 & 2 |
| Autonomy-depth | memory-driven idle, real goals, journal, self-improvement | 1 & 2 |
| Evidence/docs | test count 397, no over-claim, PASS HOLD honest | 1 & 2 |

## 10. Hard Rejection Criteria

The continuation **FAILS** if any of these hold after implementation:
1. Implementation is docs-only (no real code change to adapters/graph/state).
2. Discord proof is missing (no live dashboard/log showing memory-driven agenda).
3. Raw `LLMRouter.chat` is used as brain path (must be `HermesBrain.think`).
4. Guinevere still only repeats health-check loops with no memory/daily-life context.
5. Any sub-agent has no output file.
6. Tests/audits skipped to pass; warnings/errors hidden.
7. Secrets appear in output/evidence.
8. Production claimed PASS without live proof.
9. `world_model_available = False` placeholder still present.
10. `idle_node` still uses `random.choice`.
11. `p16_adapter`/`p18_adapter` still return `_placeholder:True`.
12. HARD STOP regression (no longer halts + recovers).
13. Any of the 7 other guinevere-* services disturbed by the deploy.

## 11. Final Allowed Statuses

- `CONTINUATION IMPLEMENTED — DEPLOYED — SOAK/OBSERVATION IN PROGRESS`
- `CONTINUATION IMPLEMENTED — LOCAL PASS — DEPLOY BLOCKED with exact blocker`
- `P20 PRODUCTION PASS` only if all live gates + clean soak actually satisfied.

## 12. Research Sources (read by orchestrator)

- `research/gap-auditor.md` (AC-LIFE matrix, 59 gaps)
- `research/life-kernel-architecture.md` (graph topology, 9 arch gaps)
- `research/memory-worldmodel-integration.md` (real API design, 7-step plan)
- `research/discord-visible-autonomy.md` (dashboard living-state gaps)
- `research/daily-life-domain-minds.md` (domain dispatch missing)
- `research/deploy-runtime-safety.md` (deploy/rollback/HARD STOP procedure)
- `research/evidence-consistency.md` (test count 397, doc over-claims)
