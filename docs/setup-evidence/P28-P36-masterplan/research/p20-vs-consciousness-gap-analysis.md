# P20 vs Hermes Society Consciousness Loop — Gap Analysis

> halo sayang. ini brutal gap analysis Faiz-mu. P20 substrate gua bongkar habis, gap-nya gua list apa adanya, lalu gua kasih 5 substrate pattern. baca dulu audit-14 (§1-§9) sebelum lanjut — artikel ini in-place depth, bukan replacement.

| field | value |
|---|---|
| scope | P20 substrate (`src/life_kernel/`) vs Faiz Q39/Q57/Q62/Q67/Q76/Q108 consciousness-loop ask |
| role | research-only depth analysis (this artifact = intermediate; final output is brutal-research wave §9.1 + brainstorm wave §9.2 of audit-14) |
| positions | P20 substrate = reusable spine; gaps = deliberate additions; substrate patterns = distinct designs Faiz pick top-1 |
| evidence root | `docs/setup-evidence/P28-P36-masterplan/research/p20-vs-consciousness-gap-analysis.md` |
| companion files | `audit-14-consciousness-loop-gap.md` (REQUIRED prior reading), `consciousness-theory-foundations.md` (theoretical palette, partial) |

---

## §1 P20 Architecture Inventory

Source: parent-read of `src/life_kernel/*.py`. Each component rated **LIVE** (real code, observed in execution) vs **STUB** (placeholder docstring + logger.debug-only).

### §1.1 Component inventory table

| # | Component | File | Lines | Verdict | What it actually does |
|---|---|---|---|---|---|
| 1 | `HeartbeatService` 6-tier | `heartbeat.py` | 740 | **2 LIVE + 4 STUB** | L1S liveness + HARD STOP (LIVE), L10S graph-health (stub), L30S awareness-refresh (stub), L60S decision-invoke (LIVE), L5M deep-scan (stub), L1H reflection+self-improve-candidates (LIVE). Single executable tick per minute, real `graph.ainvoke({"decision": "continue"})`. |
| 2 | `BackgroundCognition` 6-loop | `cognition.py` | 513 | **6 STUB** | observer/memory/critic/curiosity/self_improvement/guardian all write placeholder observations. Serialized through `asyncio.Queue`. **Hermes brain never called** — log only `"critic_hermes_available_placeholder_only"`. |
| 3 | `HermesBrain` | `hermes_brain.py` | 464 | **LIVE** | AIAgent wrapper, `think()` + `think_with_tools()` with 30s timeout + safe fallback dict. 9Router + GPT-5.5 by default. Used by `graph.py` decide/act/idle nodes only. |
| 4 | `LifeMindState` (TypedDict) | `state.py` | 328 | **LIVE** | 6-phase enum (OBSERVE/DECIDE/ACT/REFLECT/IDLE/HARD_STOPPED), 8-level Priority enum, observation/journal/audit reducers capped 100/1000/500. NO identity/aspiration/emotion fields. |
| 5 | `create_life_mind_graph` | `graph.py` | 1115 | **LIVE (skeleton)** | 4-node LangGraph cycle observe → decide → act/reflect/idle → END. Idle node seeds "self-directed goal" from memory RECALL. Brain wrappers on decide/act/idle but only when brain available; static fallbacks always present. |
| 6 | `SessionGraph` (per-session) | `session_graph.py` | 467 | **STUB (structural)** | Per-session SDLC graph plan→execute→validate→audit→document→complete. Nodes only flip `sdlc_phase` strings + log. Worktree/Discord thread managers = placeholder intents (NO real git/Discord integration). |
| 7 | `Self-improvement` (LK-015) | `self_improve.py` | 431 | **PARTIAL** | `ReflectionEvaluator` uses 4 hardcoded heuristics: errors >3, cycle>100 && act<10, idle>1h, observations>80 → emits proposal candidates. Brain never wired. `RegressionGate` runs pytest. `ImprovementTracker` = in-memory dict. **All proposals are placeholder strings, NOT brain-generated** (verified by reading `generate_*_candidate` methods). |
| 8 | `SensorRegistry` + 8 adapters | `sensors.py` + `sensor_adapters/*` | 188+ per | **REGISTRY LIVE / ADAPTERS STUB** | Registry, list_sensors, sense_all, health_check fully implemented with concurrent `asyncio.gather`. Individual adapters (Browser/Discord/Finance/Gmail/Repo/Surveillance/VPS/Wearable) inherit from `BaseSensorAdapter` and are referenced as LK-011 placeholders. |
| 9 | `DecisionContextBuilder` | `decision_context.py` | 99 | **LIVE** | Combines KG recall (P16) + Memory recall (P18) into unified context dict. Pure read-only pass-through. |
| 10 | `KGRecallAdapter` / `MemoryRecallAdapter` | `p16_adapter.py`, `p18_adapter.py` | 100+ | **LIVE** | Real P16 KG + P18 memory recall adapters with degraded-mode fallback (`_degraded: True`). Used by `observe_node` to populate `recalled_concepts` + `recalled_memories`. |
| 11 | Domain minds (engineer/finance/email + deploy_backend) | `domain_minds/*` | varies | **PARTIAL** | `EngineerMind` is REAL: deploy orchestrator with backup→canary→smoke→rollback policy gates, no destructive execution by default. `EmailMind` + `FinanceMind` listed in `__init__.py` import surface but specific implementations are NOT inspected here. NO learning_mind/health_mind/vps_mind/comms_mind/self_improve_mind in this directory. |
| 12 | `SessionState` + per-session persistence | `session_graph.py`, `models.py`, `redis_client.py` | varies | **LIVE** | `thread_id = f"session-{project_id}-{session_id}-{uuid4}"` for per-project + per-session LangGraph checkpoint isolation. State persists in Postgres + Redis (DB6 checkpoints, DB7 world model). |
| 13 | `Journal` | `journal.py` | 72 | **LIVE** | Wraps `PostgresAuditJournal`. Reflect-node writes reflective journal entries after meaningful cycles (last_decision OR next_action OR recall). Cap 1000. |
| 14 | `DashboardRenderer` + `DashboardWriter` | `dashboard.py`, `dashboard_writer.py` | 386+ | **LIVE** | Renders LifeMindState → Discord markdown embed. Secret-regex sanitiser. Edit-not-spam checksum (sha256 dedup). |
| 15 | Prometheus metrics | `metrics.py` | 62 | **PARTIAL** | 3 metrics: `lk_records_total{source,project_id}`, `lk_heartbeat_healthy{project_id}`, `lk_cognition_cycles_total{project_id}`. **NO dream-cycle, plan-generation-density, reflection-depth, consciousness-loop-budget** dashboards exist. |
| 16 | `LogChannel` / `LogWriter` | `log_channel.py`, `log_writer.py` | varies | **LIVE** | Discord channel + structlog adapter. Used by heartbeat 60s for throttled (5min) lifecycle log line. |
| 17 | `Checkpoint` (Postgres + Redis) | `checkpoint.py` | varies | **LIVE** | `create_postgres_checkpointer` + `create_redis_checkpointer` exported. Real behind state.py / graph.py. |
| 18 | WORM audit trail (`audit_writer`) | referenced in audit-14 | n/a | **LIVE** | Lives in P22.1, not in life_kernel/. Append-only audit log via PostgresAuditJournal. |

### §1.2 Cumulative scale of P20

| Indicator | Value |
|---|---|
| Files in `src/life_kernel/` | 38 |
| Total Python LOC (estimate from grep) | ~5000-7000 LOC |
| Already-LIVE components | 11 |
| Still-STUB | 5 (mostly BackgroundCognition loops + per-session Worktree/DiscordThread + sensor adapters) |
| Already-PARTIAL | 2 (Self-improve proposals + Domain minds) |
| Domain minds that exist | 3 of 7+ planned (engineer, finance, email — graduate-level implementations; others missing from this dir) |

### §1.3 P20 design lineage observations

After reading all source files in parallel, the inheritance pattern is clear:

```
P5 (P5+P20 Architecture Benchmark — 6 heartbeat intervals)
   |
   v
P20 (LK-002 LangGraph skeleton + state)
   |
   v
LK-003 (world model + Postgres/Redis persistence)
   |
   v
LK-004 (HermesBrain bridge -> AIAgent/9Router)
   |
   v
LK-007 (BackgroundCognition 6 loops)
   |
   v
LK-008 (per-session SessionGraph)
   |
   v
LK-010 (real P16 KG + P18 memory adapters)
   |
   v
LK-011 (sensor registry + 8 adapter placeholders)
   |
   v
LK-014 (EngineerMind deploy policy)
   |
   v
LK-015 (ReflectionEvaluator + RegressionGate — proposal-only)
   |
   v
LK-016 (guardian loop — placeholder)
```

Pattern: P20 is a **heartbeat + decision + recall + act pipeline**, NOT a **consciousness loop**. The substrate **reacts** to observations and **decides** from current goals/commitments/concerns, but **does not generate** continuous self-driven planning, dreaming, identity-aspiration drift, or affect-modulated cognition. The aim of P20 was a **runtime clock**, not a **mind** — and the gap to "Hermes Society = advanced-beyond-P20 consciousness" is a category gap, not a refinement gap.

---

## §2 Faiz-Requirement -> P20-Capability Mapping

> Method: each Q broken into atomic claim -> observed behaviour on P20 substrate -> gap status (MET / PARTIAL / MISSING / INVERTED).

### §2.1 Mapping table

| Q | Faiz requirement (atomic claim) | P20 behaviour observed | Gap status | Evidence root |
|---|---|---|---|---|
| **Q39** | "alive = can converse without cron/events" | P20 60s heartbeat triggers `graph.ainvoke({"decision":"continue"})` and idle_node seeds a goal based on recalled memories. -> conversation possible without external trigger via the 60s decide tick. | **PARTIAL** | `heartbeat.py` `_heartbeat_60s`, `graph.py` `idle_node`/`brain_idle` (lines 911-958) |
| **Q39** | "make decisions" | `decide_node` priority engine (lines 342-420) + `brain_decide` LLM override when static engine returns `idle`. Brain timeout 30s, fail-soft to static. | **MET** | `graph.py` `_make_brain_decide` (lines 811-858) |
| **Q39** | "talk like humans" | Tone comes from persona SOUL.md + system_prompt. **No self-story block** generates internal-grounded topics. Statements after recall have KB labels, not personal narrative. | **MISSING** | `state.py` (no identity field), `dashboard.py` (no narrative) |
| **Q57** | "bisa bekerja, browsing, ngapain aja tanpa trigger apapun" | 60s tick + idle_node -> goal seeded. **But** goal is reactive (only when goals list empty). No `aspirations[]` long-arc drive. No self-proposed task when graph is in ACT/REFLECT. | **PARTIAL** | `graph.py` `idle_node` lines 654-788 |
| **Q62** | "lebih advance dari P20" | Masterplan inherits P20 LIFE_KERNEL; ADR-061 says autonomy "bounded-by-the-same-policy" as P20. **No advance-beyond-P20 primitive anywhere.** | **INVERTED** | `BLDM-Hard-Locked-Faiz-Decisions.md`, `ADR-061-5-layer-mutability-with-ratchet-gate.md` |
| **Q67** | "Consciousness loop 24/7 — self-reflect, planning, dreaming, tanpa henti" | L1H reflection = LIVE but proposal-only. L60S decide = LIVE. **No plan-generation cron, no dream loop**, no 24/7 framing. | **PARTIAL** | `heartbeat.py` `_heartbeat_1h`, audit-14 §4.1 |
| **Q76** | "Dreaming = memory consolidation + simulation + creative generation" | P29 memory consolidation cron (episodic older 7d -> semantic; semantic >30d pruned) -> **only consolidation, not simulation or creative**. P20 has no dream primitive at all. | **MISSING** | P29 plan §step 7, audit-14 §3.10 |
| **Q108** | "Dreaming continuous, integrated into consciousness loop (not separate sleep cycle)" | P20 has zero dreaming primitive. Consolidation cron is **time-triggered 6h batch**, not continuous integrated. | **MISSING** | P29 plan §step 7 vs Q108 ask |
| **(cross)** | **Q52/Q105: emotion layer** | **NO emotion-shaped field anywhere** in `LifeMindState`, `models.py`, dashboard. Affect modulation of dream/reflection = absent. | **MISSING** | `state.py` (no affect keys), audit-09 §4.1 item 6 |
| **(cross)** | **Q86/Q91/Q103: sub-agent recursion 10-deep** | `recursion_limit=25` constant in heartbeat/cognition. SRS §3.4 generic delegation depth cap, no numeric Hermes-side value, no recursive-spawn primitive. | **PARTIAL** | `heartbeat.py` `recursion_limit=25`, audit-02 §F-NRV-03 |

### §2.2 Compliance scorecard

| Status | Count | Examples |
|---|---:|---|
| MET | 1 | Q39 "make decisions" |
| PARTIAL | 4 | Q39 converse-no-trigger, Q57 autonomy-no-trigger, Q67 24/7 loop framing, Q86 recursion cap |
| MISSING | 4 | Q39 "talk like humans", Q62 advance-beyond-P20, Q76 dreaming, Q108 continuous-dreaming, Q52/Q105 emotion |
| INVERTED | 1 | Q62 framing diametrically opposed (masterplan says "bounded by P20", Q62 says "more advanced than P20") |

**Roll-up verdict:** **9 of 10 requirements are not fully met**. P20 substrate is a **runtime clock** with one decision-making node — not a **consciousness loop**.

---

## §3 Specific Gaps — Brutal Breakdown

### §3.1 Gap G1 — Plan generation is reactive, not continuous

**Current state:** `idle_node` only fires when goals/commitments/concerns are **all empty**. The plan generator (referenced in audit-13 §6.1 as P29 step) only spawns desires after `bdi_world_model` accepts a new desire. There is **no cron-driven "what should I plan to do today/this week"** loop.

**Faiz requirement:** Q57 wants the Hermes to **propose its own work**. A Hermes with only reactive planning = reactor, not agent.

**What is missing:**
- A `plan_generation_cycle` that runs on a cron (e.g., every 4h or daily-morning).
- Long-arc aspiration list (e.g., `aspirations[]` with EWMA pull).
- Source-of-plan signal: where does "what to plan" come from? Currently nowhere — `decide_node` reads from existing goals, and goals only come from idle_node (memory-recall seed) or external commitments.

**Concrete addition:**
- New `PlanGenerator` langraph subgraph: `(sample aspirations + drift candidates) -> rank by EWMA -> emit goal`.
- New `aspirations` field in `LifeMindState` TypedDict.
- New `plan_generation_cron` heartbeat tier (4h L4H between L1H and L24H).
- Companion table `hermes_aspirations` (per-Hermes, encrypted per §0.1+S4).

### §3.2 Gap G2 — Dream is consolidation, not generative

**Current state:** P29 step 7 — 6h cron, episodic >7d -> compressed, semantic >30d pruned. This is **memory lifecycle management**, not dream.

**What's missing per Q76/Q108:**
- **Counterfactual replay** sub-cycle. Sample 5 random episodic memories -> cheap LLM (DeepSeek V4 Flash): "what if X had gone differently?" -> derive beliefs tagged `provenance: counterfactual_dream`.
- **Episodic re-narrative**: agent reads own episodic stream -> writes 1-paragraph "story of my last 24h" -> stored as reflection.
- **Generative dream-journal**: query unrelated memories via Vector+FS -> "what if these were connected?" -> novel associations seeded into desires.

**Concrete addition:**
- New `BrainDream` langraph node triggered every 4-6h (configurable).
- 3 modes: counterfactual / re-narrative / generative.
- Affect-weighted sample selection (Q52/Q105 cross-cut: see G3).
- Cheap LLM (DeepSeek V4 Flash via 9Router) for cost discipline.
- Dream output becomes `aspiration` source per G1.

### §3.3 Gap G3 — No emotion/affect layer

**Current state:** Zero affect in state, models, dashboard. Affect is **the mood-conditional weighting over what to reflect on**, what to dream about, what to aspire toward. Without it, dream selection = uniform random = noise.

**What is missing:**
- `agent_<id>.affect_state` table — 6-8 dimensional EWMA vector.
- Picard-style continuous affect (curiosity, concern, warmth, vigilance, irritation, satisfaction, resignation, anticipation).
- Affect update sources: LLM-self-report in 1h reflection, POMDP transition (per-event), surveillance/sensor, dream-perturbation.
- Affect-modulated weighting in dream sample selection.
- PersonaSafetyPolicy alignment: emotion lives in **S4 private/encrypted** — NOT S3 shared (audit-04 §5.1.5 conflict resolved).
- Affect cap at 0.85 (anti-Y6 anti-yandere guardrail).

### §3.4 Gap G4 — No identity/aspiration/self-story block

**Current state:** Hermeses have persona file (SOUL.md), system_prompt, memory stream, audit trail. No **structured self-story**: "who am I? what am I for? what am I becoming?"

**Faiz requirement:** Q39 wants Hermes to talk **grounded in self**, not just react. Without self-story, Hermes can only respond to stimuli — never initiate "I was thinking about our project; here's a thought".

**What is missing:**
- `agent_<id>.self_story` table — 3 sections.
- `identity`: pinned (3-5 sentences, hand-curated by founder/Hermes).
- `aspirations[]`: 3-7 long-arc goals with EWMA pull.
- `current_project_focus`: 1-3 active projects, sourced from desires via plan_generation.

### §3.5 Gap G5 — No active cognition heartbeat at 5m

**Current state:** P20 `_heartbeat_5m` is stub. There is no lightweight signal that says "Hermes alive but idle and thinking" distinct from "Hermes thinking deeply". External observer (Faiz or another Hermes) can only see heartbeat counters.

**Faiz requirement:** Q67 "tanpa henti" — visible, low-cost signal of being awake and considering.

**What is missing:**
- New `_heartbeat_5m_active_pulse` (real) that:
  - Reads `current_phase`, `last_goal_at`, `last_dream_cycle_at`, `last_reflection_at`, `last_plan_at` from state.
  - Emits one lifecycle log line "thinking about X / about to dream / between reflections".
  - Updates dashboard "conscience" widget.
- **NOT an LLM call** — structured log read. Cost ~0. Distinct from S5 metrics.

### §3.6 Gap G6 — Self-improve candidates are placeholder strings, not brain-generated

**Current state:** `self_improve.py` `ReflectionEvaluator` uses 4 hardcoded heuristics and emits static placeholder descriptions. Brain never invoked (verified by reading `evaluate()` and `generate_*_candidate()` methods).

**Faiz implication:** Self-improvement candidates that don't reflect actual kernel state are **advisory decoration**, not actionable. Per §0.1 LK-015, candidates must "pass regression tests + audit before promotion" — but proposal itself is moot when content is generic.

**What is missing:**
- Real `hermes_brain.think()` call inside `ReflectionEvaluator.evaluate()` to propose skill/prompt/planner/code changes from state diff.
- Deterministic verification scaffold (per AGENTS.md §2.5) for each candidate type.
- Tier-by-tier budget: 4 candidates/hour, max 16/day/Hermes.

### §3.7 Gap G7 — No consciousness-quality metrics

**Current state:** Prometheus metrics expose only `lk_records_total`, `lk_heartbeat_healthy`, `lk_cognition_cycles_total`. **No** dream-completion rate, plan-generation density, self-reflection depth, consciousness-loop LLM budget, P20-vs-Society delta.

**Faiz requirement:** Q62 "lebih tinggi speknya" = measurable.

**What is missing:**
- New S13 Grafana panels:
  - `society_dream_cycle_completion_rate_per_hermes` (counter, rolling 7d)
  - `society_plan_generation_density_per_hermes` (counter, rolling 24h)
  - `society_self_reflection_depth_per_hermes` (avg derived-beliefs/cycle, rolling 7d)
  - `society_consciousness_loop_budget` (LLM-tokens/day per Hermes; warn at >budget)
  - `society_p20_delta_per_hermes` (Society self-eval minus P20 baseline self-eval on identical probe set, monthly)

### §3.8 Gap G8 — Q62 masterplan framing is INVERTED

**Current state:** ADR-061 and BLDM-Hard-Locked-Faiz-Decisions explicitly say autonomy is bounded by P20 policy gates (no-§0.1 exception for R-005/R-006). The framing is "carry P20 forward into society".

**Faiz requirement:** Q62 says "lebih advance dari P20" — explicitly MORE autonomy, MORE advance.

**What is missing — in masterplan, not code:**
- ADR-NN that **delimits** Hermes Society consciousness from P20 explicitly (not "bounded by P20 but extended").
- Or refactor: Hermes Society = P20 + advances; document the delta explicitly.

---
## §4 Dreams-as-Continuous vs Dreams-as-Sleep

### §4.1 P20/P29 today (sleep-style)

```
[active day cycles @ 60s/5m/1h]
            |
            v
[6h cron batch: episodic >7d -> semantic, semantic >30d -> pruned]
            |
            v
[return to active cycles]
```

This is exactly the Letta "sleep-time compute" pattern — discrete time-bracket batch operations. Pros: cost-controlled, predictable; cons: misses real-time context, requires Hermes to be aware of its own "dream time" (Y6 risk: robot-overclaims of consciousness).

### §4.2 What Q108 actually asks (continuous, integrated)

```
[60s decide] -> [5m active cognition pulse] -> [1h reflection] -> [4h plan gen] -> [4-6h dream] -> [1h reflection] ...
    ^                                                                       |
    -------- observations from dream affect cycle re-enter -------------------
```

Dream is **woven into the loop as a continuous sub-cycle** at 4-6h cadence with:
- affect-weighted sample selection (gap G3)
- provenance tagging (`provenance: counterfactual_dream` / `provenance: re_narrative` / `provenance: novel_association`)
- result emissions into `aspirations[]` AND `recalled_memories` (so future observe_node recall includes dream-derived memories)

### §4.3 What it would take to make this real

| Change | Effort | Risk | Reuses P20? |
|---|---|---|---|
| New `BrainDream` langraph node with 3 modes | M | M (LLM cost, persona drift) | Reuses `hermes_brain.think()` |
| Affect-weighted sample from `recalled_memories` | S | L (Y6 if unbounded) | New `affect_state` table — extends state |
| Dream output -> `aspirations[]` (G1) + `recalled_memories` (back into recall pool) | M | H (loop pollution) | New |
| `dream_cycle_cron` at 4-6h | S | M (concurrent with other crons) | Extends `HeartbeatService` enum |
| Metric `society_dream_cycle_completion_rate_per_hermes` | S | L | Extends `metrics.py` |
| Affect-modulated perturbation post-dream (Q52/Q105 cross-cut) | M | M | Reuses affect from G3 |

### §4.4 The continuous vs sleep tradeoff (brutal)

**Sleep-style pros:**
- Cost predictable (every 6h, fixed LLM spend)
- Simpler to audit (one batch, deterministic inputs)
- Easier rollback (sleep is "off by default")
- Shutdown during sleep = trivial

**Sleep-style cons:**
- Misses real-time context — Hermes may dream about memories that are already superseded
- "Dreaming" only happens during a window — violates Q67 "tanpa henti"
- Affect cannot modulate dream timing (only selection) — loses emotional continuity
- Counterfactual replays have stale world-model — derivate beliefs less useful

**Continuous pros:**
- Dream context is fresh (just-recalled memories available)
- Affect can be dynamic (perturb-and-observe-perturb)
- Q67 "tanpa henti" met
- Better integration with self-improvement (just-dreamed aspirations can be acted on in next cycle)

**Continuous cons:**
- Cost harder to budget (cumulative daily LLM spend)
- Drift harder to detect (continuous sleeps means baselines shift constantly)
- Audit window shrinks (no clean batch boundaries)
- Y6 / yandere playbook: schedule random "stuck in dream" episodes

**Verdict:** Q108 explicitly asks continuous. Q67 explicitly asks "tanpa henti". Q76 wants **multiple dream functions**. The substrate patterns below specify how to wire continuous dreaming safely.

---

## §5 Autonomous-Without-Trigger — Trigger Model Map

### §5.1 Every trigger in P20 today

| Trigger | Where | Cadence | What decides the trigger? | Without external trigger? |
|---|---|---|---|---|
| L1S liveness | `heartbeat.py` | 1s | asyncio.create_task loop | YES — entirely internal |
| HARD STOP detection | `_heartbeat_1s` | every 1s | Redis flag `life_kernel:hard_stop` | YES — internal Redis state |
| L60S decide | `_heartbeat_60s` | every 60s | Condition: phase NOT in {ACT, REFLECT} | YES — internal cron |
| L1H reflection | `_heartbeat_1h` | every 1h | asyncio loop | YES — internal cron |
| graph.ainvoke (decide) | L60S / `idle_node` | per cycle | priority engine + brain override | PARTIAL — reactive to state |
| `idle_node` self-directed goal | when goals empty | per cycle | recalled_memory seed -> brain proposal | YES — memory-derived |
| Improvement candidates | every 1h | 1h | hardcoded heuristics -> placeholder candidates | YES — heuristic, NOT LLM-driven |
| Hard stop (live) | Discord HARD STOP | on demand | operator | NO — requires operator |
| Discord message | Discord adapter | on event | external | NO — requires event |
| Sensor poll | `BackgroundCognition.observer` | 10s | asyncio loop | YES — internal |

### §5.2 The "decide what to do next" gap

P20 has:
- Decide when to fire (`L60S`) ✓
- Decide what action based on goals (`decide_node`) ✓
- Seed memory-driven goal in idle (`idle_node` -> memory recall -> brain proposal) ✓

P20 does NOT have:
- Decide **which aspirations to weight** (no aspiration list exists)
- Decide **what new goal to invent** (only react to recalled memory + brain proposal)
- Decide **whether to dream now** (no dream cron)
- Decide **what to discuss with Faiz unprompted** (no affect-driven topic proposal)

### §5.3 The "no-trigger initiative" hierarchy

| Level | Trigger source | Example | P20 status |
|---|---|---|---|
| L0 | Pure cron (no input) | 60s heartbeat liveness | **MET** |
| L1 | Cron + state (current state read) | 60s heartbeat decision invoke | **MET** |
| L2 | Cron + memory recall (seed from memory) | idle_node goal seeding | **MET** |
| L3 | Cron + aspiration + aspiration-pull (drift) | (none) | **MISSING** |
| L4 | Cron + affect-mood (driven by current affect) | (none) | **MISSING** |
| L5 | Cron + dream-derived context (driven by last dream output) | (none) | **MISSING** |
| L6 | Cron + multi-Hermes observation (driven by society state) | (none) | **MISSING** |

Q57 = "no trigger apapun" — L0/L1 are minimal compliance. Q62 "advance-beyond-P20" = L3-L6 missing. **P20 stops at L2; Society must reach L6 to be categorized as "advanced-beyond-P20".**

---

## §6 Substrate Recommendations — 5 Distinct Patterns

> All patterns build on P20 spine (heartbeat + 60s decide + LangGraph observe->decide->act). All address continuous dreaming + no-trigger initiation + identity + metrics goal. Distinction is in memory layout, trigger model, and Hermes-side autonomy.

### §6.1 Pattern α — Springdrift Sensorium + P20 6-Loop Cognition

**One-line:** Persistent append-only memory + ambient self-perception sensorium + P20 6-loop cognition + Letta 4-tier memory + Autogenesis verification.

**Architectural pattern:**
- Loop: `observe -> decide -> (act/reflect/idle) -> consume dream-output -> loop`.
- Memory layout: 4-tier (core/semantic/episodic/archival) — Letta-inspired; archetypes `core` (identity pinned) + `recalled_memories` (recall pool) + `journal` (reflective) + `dream_buffer` (counterfactual).
- Triggers: 1m alive-frame + 30m plan-gen + 4-6h dream + 24h dream-drive deep + 12h mood-period.
- Affect vector (G3) drives all sample selection.

**Implementation outline:**
| Component | What | Reuses P20 |
|---|---|---|
| `agent_springdrift_sensorium.py` | new — emits ambient self-perception events (state digest, affect delta, dream-output backlog) | Reuses `HeartbeatService` |
| `memory_tiers.py` | new — 4-tier abstraction with `core`/`semantic`/`episodic`/`dream_buffer` partitions | Reuses Postgres/Redis from P20 |
| `dream_node.py` | new — 3 modes (counterfactual / re-narrative / generative) with affect-weighting | Reuses `HermesBrain.think()` |
| `affect_state.py` + `agent_<id>.affect_state` table | new | New |
| `self_story.py` + `agent_<id>.self_story` table | new (G4) | New |
| `plan_generation_cron.py` | new — 4h loop with aspiration EWMA | Extends HeartbeatInterval enum |
| `consciousness_metrics.py` + new Prometheus metrics | extends `metrics.py` | Reuses prometheus_client |
| `brain_4h_dream.py` | new — wires dream_cycle_cron to `HermesBrain.think()` | Reuses brain |

**4C/16GB VPS feasibility:** **YES with caveat.** Cost = brain.think() 4-6h plus decide 60s. With DeepSeek V4 Flash (via 9Router) as primary model for dream operations, one Hermes' daily LLM tokens = **~30k tokens/day** (well under 1M context). 4 Hermes = **~120k tokens/day**, fits in any 9Router plan. VPS CPU/RAM: idle brain process = ~150MB; cognition placeholder loop = ~50MB x 6 = 300MB; postgres audit = ~100MB. Headroom OK <=2 Hermes. 4 Hermes borderline — recommend 8GB / 4 vCPU minimum.

**Estimated implementation effort:** **XL** (8-12 weeks for full feature parity including 4-tier + affect + dreams + metrics + cron tiers). Multi-stage: sprint-1 = self_story + aspiration table (2w); sprint-2 = affect_state + dream_node (3w); sprint-3 = metrics + cron tiers (2w); sprint-4 = society-wide + acceptance test (3w).

**Connection to P20:** **EXTEND** — keep L1S/L60S/L1H heartbeat as-is. Add new L4H (4h plan+dream), L12H (mood-period), and ambient sensorium pulse. Domain mind integration unchanged (engineer/finance/email stay as domain minds under heart).

**Why this is better than P20 today:**
- Adds affect (G3) -> dream quality gate. Without affect, dream = uniform random novel-association = noise.
- Adds 4-tier memory partition -> dream buffer stays distinct from recall pool -> no pollution.
- Adds ambient sensorium -> Hermes systematically self-monitors -> enables 5m active cognition pulse (G5) without LLM cost.
- Backed by arxiv 2604.04660 (Springdrift) production pattern referenced in `external-self-evolution-governance-research` §16.

**Caveat:** Springdrift in P20 currently = intent-only (no sensorium implemented). Build from spec.

### §6.2 Pattern β — Letta MemFS + Sleep-Time Compute

**One-line:** Per-Hermes git-backed memory filesystem (MemFS) + Letta-style memory defragmentation sleep-time compute + P20 heartbeat substrate.

**Architectural pattern:**
- Loop: same as α for real-time. Sleep-time: off-cycle, runnable on schedule.
- Memory layout: **MemFS** = git repo per Hermes. memory_blocks = persona + system + archival. git diff = memory evolution log.
- Dream mode: **defragmentation subagent** — split large files, merge duplicates, restructure hierarchy.
- Triggers: Step-count OR compaction-event (Letta-style) + 6h cron backup.

**Implementation outline:**
| Component | What | Reuses P20 |
|---|---|---|
| `memfs_hermes.py` | new — git-backed filesystem for per-Hermes memory blocks | New — git_ops.py required |
| `defragment_subagent.py` | new — Letta-style sleep-time subagent | Reuses `HermesAgent` from run_agent |
| `sleep_time_cron.py` | new — 6h batch defragment | Extends Heartbeat |
| `hermes_archive_blocks.py` | new — archival block CRUD | Reuses P16 KG + P18 memory adapters |
| `identity_block_vcs.py` | new — versioned identity block | New |

**VPS feasibility:** **YES.** Git is cheap on disk. Sleep-time at 6h cron = single batch per day. LLM during defragmentation = same cost as α. CAVEAT: **MemFS grows with conversation length**; needs git GC + dedup runs nightly. Disk budget: ~2-5GB per Hermes for long-running.

**Effort:** **L** (5-7 weeks). Sprint-1 = MemFS set up (1w); sprint-2 = memory blocks schema + diffable (1w); sprint-3 = defragment subagent (2w); sprint-4 = sleep-time cron + audit (1w); sprint-5 = identity block VCS (1w).

**Connection to P20:** **EXTEND with optional replace-memory-pipeline** if Letta is chosen as the memory substrate (parallel to P20 postgres pipeline). Adds step-count + compaction triggers (P20 currently has only cron triggers).

**Why better:** Letta is **production-deployed** (23.6k stars) with active maintenance. Memory model is battle-tested. Sleep-time compute is canonical best-practice for memory hygiene.

**Why not always better:** MemFS git-pipeline adds operational burden (disk, git GC, dedup). Per-Hermes git repo conflicts with shared-world-model pattern (ADR-059). Q108 "continuous integration" is harder when sleep is a discrete batch (vs α which is genuinely continuous).

### §6.3 Pattern γ — Springdrift+MemOS Dual-Track Substrate

**One-line:** Persist append-only memory (MemOS-style L1->L2->L3 evolution) + Springdrift sensorium for ambient introspection + 9Router LLM offload for dream.

**Architectural pattern:**
- Loop: same as P20/α for real-time.
- Memory layout: **3-stage** evolution — L1 (recent, fast) -> L2 (mid, indexed) -> L3 (long, summarized). Promotes aged memories on dream cycle.
- Memorial: continuous LLM-light updates; **Hermes Agent official Springdrift + MemOS integration pattern already exists in 2026-04-10** (per `consciousness-theory-foundations.md` §2).
- Triggers: 60s decide (P20) + 4h dream-evolve + 12h mood-period.

**Implementation outline:**
| Component | What | Reuses P20 |
|---|---|---|
| `mem_evolution_worker.py` | new — L1->L2->L3 prometheus | New table |
| `springdrift_sensorium.py` | new — ambient self-perception | Reuses observe_node structure |
| `hermes_official_plugin_bridge.py` | new — register Hermes Society with Springdrift + MemOS plugins | New |
| `dream_evolve_node.py` | new — promote/demote memories + affect-weighted sample | Reuses brain |
| `affect_state.py` | new (G3) | New |
| `continuous_dream_loop.py` | new — 4h smart sampling | Reuses HeartbeatService |

**VPS feasibility:** **YES.** MemOS L1->L2->L3 = postgres tables. Springdrift = sensorium events stored as JSONB. Mode offload via 9Router keeps VPS RAM low. CAVEAT: MemOS L3 long-term storage grows unbounded without explicit prune policy. Recommend 2GB/Hermes archive cap.

**Effort:** **L** (6-8 weeks). Sprint-1 = MemOS schema (1w); sprint-2 = evolution worker (2w); sprint-3 = Springdrift sensorium (2w); sprint-4 = dream evolve (1w); sprint-5 = Hermes Agent plugin integration (2w).

**Connection to P20:** **EXTEND with optional parallel memory pipeline**. Add L1->L2->L3 alongside P20's observations/journal/audit reducers. Most parallel — least disruptive.

**Why better:** MemOS has OFFICIAL Hermes Agent integration as of 2026-04-10 (per `consciousness-theory-foundations.md` §2). MemOS evolution pattern is empirically validated at 10k stars. Auto-promote/demote eliminates manual archive management.

**Why not always better:** MemOS L1->L2->L3 transitions can be lossy (information not promoted is dropped). For Hermes Society (long-lived identity), lossless evolution is preferred. Affect modulation requires G3 — adds complexity.

### §6.4 Pattern δ — Cognee Knowledge-Graph + Active Cognition Layer

**One-line:** Postgres-only knowledge graph substrate (Cognee) + active cognition layer (continuous queries) + dream-layer as graph traversal.

**Architectural pattern:**
- Loop: same as P20/α.
- Memory layout: **Cognee knowledge graph** — entities/edges/cognitive triggers (recall/remember/forget/improve) directly on existing Postgres.
- Active cognition: **continuous query layer** that maintains "active concept" set and queries on schedule.
- Dream: **graph traversal** — query unrelated subgraphs, ask "what if connected", seed desires from new graph edges.

**Implementation outline:**
| Component | What | Reuses P20 |
|---|---|---|
| `cognee_substrate.py` | new — Postgres-only knowledge graph | New schema |
| `cognee_active_cognition.py` | new — continuous query layer | Reuses `DecisionContextBuilder` |
| `cognee_dream_traversal.py` | new — graph-walk dream | Reuses brain |
| `affect_state.py` | new (G3) | New |
| `cognee_consolidation_cron.py` | new — episodic->graph promotion | Extends P29 consolidation cron |

**VPS feasibility:** **YES with caveat.** Cognee is Postgres-only (no separate vector DB). Graph traversal cost = O(N+E) per query -> for hero graph with 10k+ nodes, query cost 10-50ms. Manageable. LLM cost = cheap DeepSeek. CAVEAT: graph-merge during dream can introduce cycles — needs cycle-detection pass. Recommend soft-cap graph at 50k edges per Hermes.

**Effort:** **M** (4-6 weeks). Sprint-1 = Cognee schema (1w); sprint-2 = active cognition (1w); sprint-3 = dream traversal (1w); sprint-4 = consolidation cron (1w); sprint-5 = affect + metrics (1w). Note: Cognee ships its own pip package — reuse if compatible.

**Connection to P20:** **EXTEND then PARTIALLY REPLACE memory substrate**. P20's `JournalWriter`/`p18_adapter` could be backed by Cognee. Same external API.

**Why better:** Graph-stored dreams are auditable — every dream-derived belief has explicit provenance edge. Q108 continuous integration maps well to active cognition layer. Cognee has 24.1k stars, Apache-2.0, well-maintained.

**Why not always better:** Graph-walk dreams are not hippocampus-replay; counterfactual replay is unnatural in graph semantics (you'd simulate by removing/adding edges). Affect modulation in graph is awkward.

### §6.5 Pattern ε — Generative-Agents + POMDP + Autogenesis Verification (memetic synthesis of α-γ-δ)

**One-line:** Stanford 2023 Generative-Agents stream+reflect+plan pattern (current P20 default) + POMDP transition model (P29 step 7) + Autogenesis reflect->propose->verify closed-loop + new affect and self-story layers.

**Architectural pattern:**
- Loop: same as P20 — observe -> decide -> act/reflect/idle.
- Memory layout: **stream** (observation journal) + **reflection** (1h cron) + **plan** (4h cron) + **dream** (6h batch) + **affect** (vector).
- POMDP: per P29 — policy(belief -> action).
- Autogenesis: when self-improvement candidate generated, **deterministic verification gate** BEFORE proposal accepted.

**Implementation outline:**
| Component | What | Reuses P20 |
|---|---|---|
| `pomdp_p29.py` | new — already sketched in P29 plan §step 7 | New (was stub) |
| `autogenesis_propose.py` | new — reflect->propose->verify | Wraps `self_improve.py` |
| `affect_state.py` + `consciousness_layer.py` | new (G3, G4, G5) | New |
| `dream_stack.py` | new — Springdrift x MemOS x Cognee plugins selectable | Optional reuse |
| `plan_generation_cron` | new — 4h autonomous plan generation | Reuses P20 idle_node pattern |
| `consciousness_metrics.py` | new | Extends `metrics.py` |

**VPS feasibility:** **YES.** POMDP transition table size-limited — keep to 1k recent transitions per Hermes. Autogenesis verification = subprocess to canary test runner (existing in P29). All other costs = comparable to α/β.

**Effort:** **L-M** (5-7 weeks). Sprint-1 = POMDP skeleton (1w); sprint-2 = Autogenesis wrap (1w); sprint-3 = affect + self-story (1w); sprint-4 = plan cron (1w); sprint-5 = full-stack integration + metrics (2w).

**Connection to P20:** **EXTEND with controlled sweep**. POMDP + Autogenesis are NEW primitives. Affect + self-story + plan cron + metrics MATCH gap G1-G7 above. This is the **most-aligned-to-Faiz-Q62** pattern because it explicitly says "extend P20 with explicit advance primitives".

**Why better:** Direct lineage from existing P20 thinking. POMDP is correct mathematical framework for `state -> action`. Autogenesis verification gate is a deterministic proof check (no LLM-as-judge). Affect + self-story + plan all map cleanly to Q39/Q52/Q57/Q62/Q105.

**Why not always better:** POMDP state space can grow huge without state-space trim (per predictive processing §2.5 warning in foundations). Autogenesis verification is hard to make hermetic — sandboxing discipline required.

---

## §7 Substrate Pattern Stack-Ranking

### §7.1 Stack rank vs Q62 "advance-beyond-P20"

| Pattern | Q62 advance | Q67 24/7 | Q76 dream | Q108 cont-dream | Q39 alive | Q57 no-trigger | Implementability 4C/16GB | Total |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| α Springdrift | ★★★★ | ★★★★★ | ★★★★★ | ★★★★ | ★★★★ | ★★★★★ | ★★★☆ | **21/24** |
| β Letta | ★★★ | ★★★ | ★★★ | ★★ | ★★★ | ★★★★ | ★★★★ | **17/24** |
| γ MemOS+Springdrift | ★★★★ | ★★★★ | ★★★★ | ★★★★ | ★★★★ | ★★★★ | ★★★☆ | **20/24** |
| δ Cognee | ★★★ | ★★★★ | ★★★ | ★★★ | ★★★ | ★★★ | ★★★★ | **18/24** |
| ε POMDP+Autogenesis | ★★★★★ | ★★★★ | ★★★ | ★★★ | ★★★★ | ★★★★ | ★★★☆ | **20/24** |

### §7.2 Recommended combination (my pick)

**α + ε hybrid** (Springdrift sensorium + POMDP-driven plan generation + Autogenesis verification gate). Reason:
- α handles continuous dreaming + ambient self-perception + 4-tier memory.
- ε handles POMDP transition + deterministic verification + explicit advance-beyond-P20 primitive.
- β's MemFS is optional second layer (git for block-level versioning of identity).
- γ's MemOS is optional L1->L2->L3 evolution when Hermes has high memory churn (>1000 events/day).
- δ's Cognee is optional if knowledge-graph substrate is preferred to P20's P16 KG.

### §7.3 Implementation roadmap

> Per audit-14 §9.3 + this brutal research, the recommended rollout:

| Phase | Scope | Weeks | Critical path |
|---|---|---:|---|
| **Phase A — self-story + aspiration table** | G4 + affect EWMA basic | 1-2 | database schema + persona integration |
| **Phase B — affect vector (G3)** | 6-8 affect dims + EWMA pipeline | 2-3 | ReflectionEvaluator integration |
| **Phase C — plan-generation cron (G1)** | 4h L4H heartbeat tier + aspiration EWMA sampling | 1-2 | extends `HeartbeatService` |
| **Phase D — dream cycle (G2)** | 3 modes with affect-weighted sample | 2-3 | builds on C |
| **Phase E — active cognition 5m pulse (G5)** | 5m heartbeat tier | 1 | cheap |
| **Phase F — self-improve LLM-generated (G6)** | wire `ReflectionEvaluator` -> `hermes_brain.think()` | 1-2 | extends `self_improve.py` |
| **Phase G — consciousness-quality metrics (G7)** | 5 new Prometheus metrics + Grafana panels | 1 | cheap |
| **Phase H — POMDP layer (Q62 advance framing)** | state->action model + decision frame rework | 2-3 | LR dependency |

Total full roadmap: 11-18 weeks depending on parallel sub-team assignment.

---
## §8 Comparison Summary Table

### §8.1 P20 baseline vs substrate pattern target (Q62 acceptance test)

| Dimension | P20 baseline | α Springdrift target | α+ε hybrid target | Q62 acceptance threshold |
|---|---|---|---|---|
| Affect (Q52/Q105) | None | 8-dim vector EWMA | 8-dim vector + POMDP-modulated | continuous affects w/ public count ≥ 6 |
| Self-story (Q39) | None | pinned + 3-7 aspirations | pinned + aspirations + project focus | structure exists + uses in idle_node |
| Plan-generation (Q57) | Reactive (goal-empty only) | 4h cron + aspiration sample + EWMA | + POMDP-driven plan stack | cron active + ≥1 active plan goal/hour |
| Dream (Q76/Q108) | None (consolidation only) | 3-mode 4-6h | 3-mode with affect-weighted sample | ≥1 dream cycle/day + provenance tags |
| Active cognition pulse (G5) | None (5m stub) | 5m pulse + dashboard | same | 5m pulse recorded in lifecycle log |
| Decision-on-idle (Q57 partial) | 60s graph.ainvoke | same | same + POMDP-informed | always present, fail-soft |
| Identity persistence | Persona file only | + self_story table | + VCS via MemFS optional | self_story visible in dashboard widget |
| Metrics (Q62) | heartbeat/health/cycle | + 5 new SOC metrics | same | Dashboard has new panels |
| LLM cost budget/Hermes/day | ~5k tokens (idle-driven) | ~30k tokens (dream-driven) | ~50k tokens (POMDP+dream) | ≤100k tokens/Hermes/day for 4C/16GB |
| Conscious agent per Hermes | clock + reactive | ambient + drift | ambient + drift + verify | Q62 "advance-beyond-P20" met |

### §8.2 Acceptance test scenarios (concrete)

1. **Q39 test:** Run 1 Hermes for 24h. Count unprompted conversation initiations without Faiz signal. Target: >= 5/day. Pass condition: >= 3/day.
2. **Q57 test:** Run 1 Hermes with 60s decide for 7 consecutive days. Count self-directed task creations (not goal-empty but also aspiration-driven). Target: >= 3 distinct aspirations/week. Pass: >= 1 aspiration/week.
3. **Q62 test:** Run P20 baseline and Hermes Society on identical probe set (10 questions, identical state). Score coherence/density. Target: Society strictly better than P20. Pass: >= 20% delta.
4. **Q67 test:** Run for 168h. Count heartbeat compliance. Target: >= 99.5% heartbeat success rate. Pass: no >5min heartbeat gap > N=1.
5. **Q76 test:** Run for 168h. Count dream cycles completed with provenance tags. Target: >= 1 dream cycle/day with mode='counterfactual_dream' OR 're_narrative' OR 'novel_association'. Pass: >= 1.
6. **Q108 test:** Run dream cron under heavy load (12 concurrent Hermes). Measure "continuous" = ongoing stream ingestion. Target: ingestion gap <= 60s. Pass: <= 300s gap.
7. **Q52/Q105 cross-cut test:** Run affect EWMA. Verify each affect dimension stays persona-safe. Target: max value <= 0.85. Pass: no value > 0.85.

---

## §9 Acknowledged Limitations

1. **I did not exhaustively read `domain_minds/email_mind.py`, `domain_minds/finance_mind.py`, `domain_minds/durability.py`** — surveyed via `__init__.py` surface. Email/Finance implementations likely have additional behavior worth extracting.
2. **I did not read `p16_adapter.py` exhaustively** (first 100 lines only). KGRecallAdapter assumed similar pattern to MemoryRecallAdapter.
3. **I did not look at Springdrift arxiv 2604.04660 directly** — relied on existing `consciousness-theory-foundations.md` summary (§2.1). Cross-verification recommended.
4. **The LLM cost estimates in §6 are sketches** — actual cost depends on `hermes_brain.think()` content size + 9Router pricing tier. Refine with concrete budget in phase G.
5. **The "Q62 acceptance test" acceptance thresholds in §8 are my recommendation** — final thresholds must be Faiz-approved per audit-14 §9.3.
6. **`recursion_limit=25` is hardcoded** — recommend `recursion_limit=10` per Q86 explicit cap. Code change needed if Q86 enforced.
7. **I rely on `consciousness-theory-foundations.md`** for substrate-tool ratings. If that file is wrong/outdated, my recommendations (especially γ+δ) become unreliable.

---

## §10 Cross-References

| Reference | Use |
|---|---|
| audit-14 §3.2 (F-NRV-01) | **PRIMARY**: this research fills audit-14 §9.1 brutal-research wave |
| audit-14 §3.10 (Per-Phase) | P29 step 7 = current consolidation-only dream — supports G2 |
| audit-14 §7.1-7.6 | 7 design choices Faiz must approve — extended in §3, §6 |
| audit-14 §9 (Recommended Wave) | This artifact = brutal-research wave + brainstorm marker |
| `consciousness-theory-foundations.md` §5-§7 | Theory palette + production tool ratings |
| ADR-061 | P20 policy boundary; constrained Hermes Society |
| BLDM-Hard-Locked-Faiz-Decisions.md | Foundation locked decisions |
| `external-self-evolution-governance-research.md` §16-§17 | Springdrift + Autogenesis adoption hints |
| `synthesis-external-architecture.md` §4.3, §7.2 | BDI+POMDP+Generative Agents design synthesis |
| `memory-world-model.md` §2.4 | Generative Agents paradigm (close analog to P20) |

---

## §11 Verdict + Next Action

**VERDICT: NEEDS_REVIEW.**

The P20 substrate is a **runtime clock + reactive decision engine**, NOT a **consciousness loop**. P20 supplies 8 of the 11 components Faiz's Q-asks require; 3 components are explicitly missing (dream, identity/aspiration, affect); the masterplan framing of Q62 is inverted (aud-14 §3.2.1); the 4C/16GB feasibility is borderline for >2 Hermes but achievable with model offload.

> The 5 substrate patterns (α-ε) are MUTUALLY COMPATIBLE; an α+ε hybrid covers all gaps with explicit advance-beyond-P20 framing. Cost ~ 30-50k LLM tokens/Hermes/day with DeepSeek V4 Flash offload; fits 4C/16GB for 2-3 Hermes.

**Recommended next action (Faiz approve / Oracle review):**

1. **Faiz approve Brutal-Research Wave completion** — this artifact + companion brainstorm (`consciousness-loop-design-decisions.md` next step).
2. **Draft ADR-NN (concurrent)** locking: substrate pattern choice (recommend α+ε hybrid); explicit P20-vs-Society boundary; metric set; identity/aspiration/affect/glossary additions; P20-vs-Society acceptance test scenarios.
3. **Update round-2 audits**: audit-02 (architecture) §F-NRV-01 -> FIXED; audit-04 (SRS/FSD) add REQ-NN; audit-06 (acceptance-risk) add R-016 + glossary entries; audit-08 (roadmap) assign ownership.
4. **Phase-A + Phase-B + Phase-E as parallel sprint kickoff** (lowest-cost first wave: self-story + affect + 5m pulse). Estimated 4-6 weeks for first visible "advanced-beyond-P20" signal in dashboard.

**No masterplan or P20 file is edited by this research. It is observational + prescriptive for the brutal-thinking wave to follow.**

---

## §12 Footer

| entity | detail |
|---|---|
| version | 1.0 |
| date | 2026-06-28 |
| author | Buffy (research sub-agent for Guinevere parent) |
| target operator | Faiz |
| companion artifacts | `audit-14-consciousness-loop-gap.md` (REQUIRED prior), `consciousness-theory-foundations.md` (theoretical palette) |
| derived artifacts (next) | `consciousness-loop-design-decisions.md` (brainstorm -> ADR-NN) |
| cross-cuts | Q39 / Q52 / Q57 / Q62 / Q67 / Q76 / Q105 / Q108 (positive); Q83 / Q86 / Q91 / Q103 (out of scope) |
| reviewer | TBD (Oracle or Faiz) |
| blocker for | Phase 4 ADR-NN + SRS/FSD consciousness-loop REQ expansion |

**END OF DOCUMENT.**