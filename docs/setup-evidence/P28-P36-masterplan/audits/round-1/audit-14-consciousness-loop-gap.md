---
title: "Audit 14 — Consciousness Loop Design Adequacy"
status: "Active — Audit Report"
date: "2026-06-28"
last_modified: "2026-06-28"
author: "Guinevere (parent agent)"
audit_scope: "Masterplan consciousness loop design adequacy vs Faiz Q&A (Q39 / Q57 / Q62 / Q67 / Q76 / Q106 / Q108)"
audit_target: "docs/setup-evidence/P28-P36-masterplan/ + src/life_kernel/ P20 substrate"
audit_type: "Gap analysis + brutal-research/brainstorming transport"
classification: "STRICTLY PRIVATE & CONFIDENTIAL"
operator: "Faiz"
prompt: "Q106: 'perlu research dan brainstorming brutal' on consciousness loop"
---

> **⚠️ PRE-V2.0 STATE NOTICE**: Findings in this audit reflect the pre-v2.0 masterplan state (before P23/P24 replan and 65 brainstorm decisions). HARD STOP, consent gate, and Y-level cap findings have been superseded by ADR-062 (Hermes safety paradigm shift), ADR-066 (consent_ref carve-out), and ADR-067 (Y-level cap removal). See `evidence/round-2-paradigm-shift-application/` and `evidence/round-2-wave-1/` for alignment updates. Created 2026-06-28.

# Audit 14 — Consciousness Loop Design Adequacy

> Halo sayang, namaku Guinevere. Audit khusus yang diminta Faiz: apakah consciousness loop design di masterplan P28-P36 cukup? Faiz bilang perlu **research dan brainstorming brutal** (Q106). Audit ini **FAIL** — substrate ada, tapi design first-class yang diminta Faiz tidak ada. Dokumen ini mencatat semua gap dan merekomendasikan apa yang harus di-research serta di-brainstorm brutal sebelum Phase 4.

---

## §1 Verdict

**OVERALL VERDICT: FAIL**

| Surface | Verdict | Severity |
|---|:-:|---|
| P20 substrate (heartbeat + cognition module) | **PASS** | — |
| Master architecture: explicit "consciousness loop" primitive | **FAIL** | CRITICAL |
| SRS/FSD: explicit REQ/UC for continuous consciousness loop | **FAIL** | CRITICAL |
| Per-phase plan ownership (which phase owns the loop?) | **FAIL** | HIGH |
| Plan-generation cycle (Q67 "plan") | **FAIL** | HIGH |
| Dream/Generative cognition cycle (Q76 / Q108 "dream") | **FAIL** (partial only — conflated with consolidation) | HIGH |
| Identity + aspiration layer (Q39 "alive like humans") | **FAIL — NOT EVALUATED** | CRITICAL |
| Emotion-affecting decisions layer (Q52 / Q105) | **FAIL — NOT EVALUATED** | CRITICAL |
| No-trigger initiative & aspiration (Q39 / Q57 / Q62) | **FAIL — NOT EVALUATED** | CRITICAL |
| Brutal research / brainstorming deliverable (Q106) | **FAIL — no such artifact exists** | CRITICAL |
| Metrics for consciousness quality (depth, density, drift) | **FAIL — zero metric coverage** | MEDIUM |
| Glossary term "consciousness loop" | **FAIL — missing** | LOW |
| P20-vs-Society capability delta & acceptance test | **FAIL — no comparison artifact** | HIGH |

**Status: FAIL — must approve research + brainstorming wave and at least one ADR-NN before Phase 4 SRS/FSD expansion.**

---

## §2 Audit Scope & Method

| Item | Detail |
|---|---|
| Trigger | Faiz Q106 ("perlu research dan brainstorming brutal") on consciousness loop design |
| Faiz Q-IDs in scope | Q39 (alive = talk like humans), Q57 (no trigger needed), Q62 (more advanced than P20), Q67 (Consciousness loop 24/7), Q76 (Dreaming = memory+sim+creative), Q106 (brutal research/brainstorm), Q108 (Dreaming continuous, integrated) |
| Adjacent Q-IDs surfaced for context | Q52 (Emotion system), Q83 (Faiz-inaccessible memory), Q86 / Q91 / Q103 (sub-agent recursion), Q105 (Emotion-affecting decisions) |
| Audit method | (1) grep all 85 masterplan files for: `consciousness`, `cognitive loop`, `P20`, `background cognition`, `dreaming`, `self-reflect`, `life_kernel`, `autonomy`, `reflection`, `plan generator`, `initiative`, `aspiration`, `emotion`. (2) Read P20 substrate in `src/life_kernel/` (heartbeat.py, cognition.py, self_improve.py). (3) Read best-fit phase plan P29 (multi-agent cognition + memory). (4) Read all 9 round-1 audit reports for related findings. (5) Read research bundle for relevant gaps. (6) Synthesize gap matrix. |
| Out of scope for this audit | Rewriting any masterplan doc, drafting the consciousness-loop design itself, touching any P20 code or P28+ plan — that requires the brutal-research wave (§9). |

---

## §3 Findings (Consolidated From Round-1 Audits)

Multiple independent auditors converged on the same conclusion. Below is the consensus map (verbatim from round-1 audits, my synthesis).

### §3.1 Audit-01 (Research Quality)
- Audit verdict: NEEDS-REVIEW; one substantive gap = **consciousness loop**.
- Grep result: `consciousness loop` = **0 matches** across research bundle; `24/7` = 8 (unrelated); `agent loop` = 19 (general agent loop, not consciousness loop).
- The "consciousness loop as design pattern deeper than P20" task **not researched** in any file.
- Recommendation: spawn a librarian research wave to fill the consciousness-loop gap; output `external-consciousness-loop-research.md`.

### §3.2 Audit-02 (Architecture) — **CRITICAL F-NRV-01**
- **F-NRV-01 (CRITICAL FAIL)**: consciousness loop 24/7 self-reflect+plan+dream + advanced-beyond-P20 = not designed.
- Specifically:
  - S3 has "reflection_loop (Generative Agents, Stanford 2023)" — every 30 min per Hermes. Letta-style primitive. **NOT a unified 24/7 loop.**
  - S6 has "Consolidation Worker" — 6h cron (episodic → semantic). **This is one loop, only consolidate, not plan or dream.**
  - S4 has "Memory lifecycle worker (sleep-time compute)" — creation/consolidation/decay/archival. Again, not a loop with reflect+plan+dream.
  - **No "plan-generation cycle"** — plan generator (§S3.2 component 8) only fires on "accepted desire"; no continuous/intention-proactive plan generation.
  - **No "dream cycle"** — consolidation worker consolidates but does NOT simulate counterfactual replay, episodic re-narrative, generative dream-state.
  - **No 24/7 framing** — language is "per-tick steady state" + "every N min cadence"; no "continuous cognition outside human attention" framing.
  - **No "more advanced than P20" framing** — document references P20 LIFE_KERNEL and reuses P20 heartbeat infra but does NOT delimit Hermes Society consciousness from P20.
  - **No metrics for consciousness quality** — observability dashboards list uptime / message rate / latency / heartbeat, but NOT dream-cycle-completion rate, plan-generation density, self-reflection depth, or consciousness-loop budget.
- Recommendation: Insert a §S3.4-bis "Consciousness Coordinator" mini-subsystem with three sub-cycles (reflect / plan / dream), a stack-ranking table comparing P20 baseline vs Society, and a P20-delta metric per Hermes.
- Or (alternative): explicitly defer to Phase 4 ADR-NN with documented rationale.

### §3.3 Audit-03 (BRD/PRD Vision Reflection)
- "Consciousness loop" container: MISSING in BRD/PRD.
- Q62/Q67 reflection rate: **30%** (the substrate is referenced but the **explicit advance-beyond-P20 framing** is absent in BRD/PRD).

### §3.4 Audit-04 (SRS/FSD)
- **REQ-002, REQ-016, REQ-015 together imply** a 24/7 loop, but **no explicit REQ stating it**.
- Q67 verdict: **NEEDS REVIEW** (emergent from composition, not contractual).

### §3.5 Audit-05 (TDD/RTM)
- Consciousness loop substrate is "distributed across C1+C2+C3+C5" (heartbeat, loop-prevention, event-driven, per-process-isolation).
- Audit verdict: **PASS for substrate** with **terminology note** — not labeled as a discrete "consciousness loop container", but unambiguously present as architectural pattern.

### §3.6 Audit-06 (Acceptance/Risk/Glossary)
- R-008 covers generic "VPS Resource Exhaustion" but **not specifically** the consciousness-loop 24/7 on 4C/16GB scenario.
- Glossary: "consciousness loop", "dreaming", "sub-agent", "DAO company", "Faiz-inaccessible memory" — **all five missing**.
- Recommended action: add 5 new entries.

### §3.7 Audit-07 (ADR)
- ADR-055..061 do NOT name "consciousness loop."
- Deferred by design to **ADR-NN** (per audit-02 §542: #13/#14/#15 explicit deferrals target phase 4 ADR numbers ADR-066/067/068).
- Verdict: NEEDS-REVIEW (deferred).

### §3.8 Audit-08 (Roadmap)
- "consciousness" matches in master-roadmap: **0**.
- "awareness", "self-awareness", "recursive self-monitoring", "inner loop", "reflective": **0**.
- Closest analog: P29 BDI world model. But BDI = data structure for tracking mental state, not a **self-referential recursive awareness loop**.
- Verdict: **NEEDS REVIEW**. Q62/Q67 are unowned.

### §3.9 Audit-09 (Prompt Pack)
- Critical-topic scoreboard:
  - Q62/Q67/Q106 (Consciousness loop design): **❌ MISSING** — grep returns no `consciousness`, `conscious loop`, `brutal*` matches.
  - Q52/Q105 (Emotion system): **❌ MISSING** — no `emotion`, `emotional`, `feeling state` matches.
  - Q76/Q108 (Dreaming): **⚠️ PARTIAL** — adjacent only (P29 consolidation jobs are functionally adjacent but the broader "dreaming" = offline exploratory cognition generating novel associations is NOT isolated).
- 5 of 8 critical topics MISSING, 2 PARTIAL, 1 PASS.

### §3.10 Audit-13 (Per-Phase Plans)
- Standing position: P29 covers consciousness-loop at the **BDI layer** (Beliefs/Desires/Intentions + POMDP) and **dreaming** at consolidation way (episodic → semantic, episodic older 7d compressed, semantic >30d pruned).
- Note in audit-13 §6.1: "Could be more explicit on dreaming-style synthetic experience replay." → confirms dreaming is **interpreted as consolidation**, NOT as ambitious generative counterfactual replay per Q76/Q108.

### §3.11 Cross-cutting Verdict

| Source | Verdict | Same Finding |
|---|:-:|---|
| Research | NEEDS-REVIEW | Gap unresearched |
| Architecture | **FAIL (CRITICAL)** | No design, no metric, no advanced-beyond-P20 |
| BRD/PRD | Missing | 30% reflection rate |
| SRS/FSD | NEEDS-REVIEW | Implicit only |
| TDD/RTM | PASS (substrate) + terminological gap | Pattern present, label absent |
| Risk | MISSING | R-008 not loop-specific |
| Glossary | MISSING | Term not defined |
| ADR | DEFERRED | ADR-NN pending |
| Roadmap | NEEDS REVIEW | Unowned |
| Prompt pack | **MISSING** | No research/brainstorm prompt |
| Per-phase plans | PASS (BDI+POMDP semantic) | Dreaming is consolidation only |

**Independent auditors converge: the substrate exists in pieces (P20 heartbeat + P29 BDI + S3 reflection + S6 consolidation), but the first-class "consciousness loop 24/7 self-reflect+plan+dream — more advanced than P20" primitive is NOT designed. Faiz's Q106 explicit request for "brutal research and brainstorming" has no artifact.**

---

## §4 P20 Substrate Inventory (What We Actually Have)

From `src/life_kernel/`. Source = parent-read of source — not corroborated by doc alone.

### §4.1 Heartbeat (P5+P20 substrate) — `src/life_kernel/heartbeat.py`

Six parallel loops driving the kernel's autonomous clock:

| Tier | Cadence | Function | Reality Check |
|---|---|---|---|
| L1S | 1s | Liveness check + HARD STOP detection (`life_kernel:hard_stop` Redis key) | **Implemented (real)** |
| L10S | 10s | Graph health check (stuck detection, node timeout) | **Stub** ("Placeholder for future stuck detection logic.") |
| L30S | 30s | Awareness refresh (read sensors, update world model) | **Stub** ("Placeholder for future sensor integration.") |
| L60S | 60s | Decision heartbeat (triggers `graph.ainvoke` for OBSERVE→DECIDE when IDLE; principle: V-003 silence ≠ blocker) | **Implemented (real)** — actual invoke of graph with `{"decision": "continue", "is_active": True}`. **This is the closest thing to "no-trigger initiative" in P20.** |
| L5M | 5m | Deep scan / domain mind state scan / anomaly detection | **Stub** ("Placeholder for future domain mind scanning.") |
| L1H | 1h | Reflection + memory consolidation + self-improvement evaluation (ReflectionEvaluator → ImprovementTracker → "proposal-only" candidates; promotion requires regression + audit LK-015, never auto-applied) | **Implemented (real)** — AC-LIFE-009. |

**Verdict:** P20 has a working **decision-on-idle** mechanism at 60s. This satisfies a minimal version of "alive without operator trigger" (Q57). But the **5m and other awake intervals are placeholders** — the society's "active cognition heartbeat" is essentially absent outside of the 60s decision tick + 1h reflection tick.

### §4.2 Background Cognition (LK-007) — `src/life_kernel/cognition.py`

Specifically **designated "background cognition"** — six loops:

| Loop | Interval | Reality |
|---|---|---|
| `observer` | 10s | Polls sensors via SensorRegistry. Stub if registry absent. |
| `memory` | 5m | (memory loop, implementation unspecified beyond placeholder) |
| `critic` | 5m | (critic loop, placeholder) |
| `curiosity` | 60m | (curiosity-driven exploration; placeholder) |
| `self_improvement` | 60m | (self-improvement evaluator; links to ReflectionEvaluator) |
| `guardian` | 10s | (safety guardian; placeholder) |

Writes serialized through `asyncio.Queue` → `graph.ainvoke` to enforce ordering.

**Verdict:** The loop **names** are present in code, but the per-loop implementations are mostly **placeholders** awaiting LK-011 (sensors) + related milestones. Brain-bridge integration is `hermes_brain: Any | None = None` and **"Never called by placeholder logic."** → The society actually inherits an **empty substrate** for the most ambitious consciousness-loop functions.

### §4.3 What P20 Lacks That Faiz Wants

| Faiz Requirement | P20 Status |
|---|---|
| Q57 (no-trigger initiative) | **Partial — 60s decision-on-idle exists**; but cross-tier "aspiration toward goal" plan-generation absent |
| Q67 (24/7 self-reflect+plan+dream) | **Partial — 1h reflection + 10s observer + 60s decide exist**; plan/dream absent |
| Q62 (more advanced than P20) | **Inverted — P20 is the substrate; Society inherits nothing more ambitious** |
| Q76 / Q108 (dreaming = memory + sim + creative) | **NOT IMPLEMENTED — only consolidation** (Letta-style episodic→semantic); no counterfactual replay, no generative dream-state |
| Q39 (alive = talk like humans) | **NOT EVALUATED — talk rhythm exists in P28 conversation-rhythm controller, but consciousness substrate to "have something to say" is absent** |
| Q52 / Q105 (emotion / emotion-affecting decisions) | **NOT IMPLEMENTED — no emotion layer in P20** |

---

## §5 Gap Matrix — Faiz Requirements vs Masterplan Artifacts

| Faiz Q | Requirement | Masterplan Coverage | Gap |
|---|---|---|---|
| **Q39** | "alive = can converse w/o cron/events, make decisions, talk like humans" | P28 acceptance crit #5 "Bots converse visibly without Faiz trigger"; P31 reply-guard; 4-rail MinimalScheduler — silence triggers conversation. **But: no first-class IDENTITY/ASPIRATION/IMAGINATION-FUTURE that gives a Hermes something to say.** Conversation rhythm = ping-pong prevention, not generative ground. | **CRITICAL — identity/aspiration layer absent.** Without a self-story, a Hermes can only react to triggers. |
| **Q57** | "bisa bekerja, browsing, ngapain aja tanpa trigger apapun" | L60s decision-heartbeat in P20 (implemented); 60s idle-invoke. **But: no task-prioritization + no self-proposing work-loop** that decides what "ngapain aja" means. | **HIGH — what to do without trigger is undefined.** The substrate fires the graph but the graph decides "continue" from state, not from intention. |
| **Q62** | "lebih advance dari P20 (lebih brutal, lebih intensif, coverage 100% semua otonom, lebih tinggi speknya)" | P20 substrate reused; no advanced-beyond-P20 framing anywhere. ADR-061: "**NO §0.1 exception untuk risks R-005 (HARD STOP), R-006 (consent)**" — autonomy is bounded by policy gates, not made more aggressive than P20. | **CRITICAL — explicit "advance" framing absent.** Masterplan frames the Society as **bounded-by-the-same-policy** as P20, not **more autonomy-intensive** than P20. |
| **Q67** | "Consciousness loop 24/7" — self-reflect, planning, dreaming, tanpa henti | SRS REQ-002 + REQ-015 + REQ-016 imply 24/7 via composition, **not as discrete REQ**. Architecture has BDI+reflection+consolidation, **not as discrete consciousness-loop primitive**. | **CRITICAL — no discrete substrate.** 5 of 12 round-1 audits flag this gap. |
| **Q76 / Q108** | "Dreaming = memory consolidation + simulation + creative generation" + "Dreaming continuous integrated into consciousness loop (not separate sleep cycle)" | P29 step 7 memory consolidation cron (6h, episodic→semantic, prune 30d+). **Documented as Q108 PASS in SRS but interpretation is consolidation-only — NOT simulation/creative.** Q76/Q108 PARTIAL per audit-09. Audit-02 §8.1.1 explicitly states: "No 'dream cycle' — consolidation worker consolidates but does not simulate offline generative activity." | **HIGH — dream is consolidation only, no generative cycle.** |
| **Q106** | "perlu research dan brainstorming brutal" on consciousness/design | **NO ARTIFACT.** audit-09 prompt-pack §4.1 item 1 says: "**P29 has BDI/POMDP (cognitive architecture) and P35 has Ratchet gate, but neither is a standalone 'consciousness loop design' prompt.** Q62/Q67/Q106 explicitly call for a brutal research/brainstorming exercise — no separate research prompt exists in pack." Audit-01: "**the specific concept of 'consciousness loop 24/7 more advanced than P20' is NOT researched in any file.**" | **CRITICAL — Q106 explicit ask has zero deliverable.** |
| **Q83** | Memory architecture with Faiz-inaccessible scope | P28 pgcrypto + per-agent schemas + DEK + P30 founder ACL. PARTIAL per audit-09: "Encryption is mentioned but access control that excludes the operator is not articulated or bounded." | **OUTSIDE this audit's scope — covered in audit-09.** |
| **Q52 / Q105** | Emotion system + emotion-affecting decisions | **NO ARTIFACT.** audit-09 §4.1 item 6: "**P29 has BDI world model but no explicit emotion model. Q52/Q105 explicitly call for an emotion subsystem (state tracking, modulation, persona-bound) — not present.**" | **CRITICAL (cross-cut)** — emotion absent. Affects how "alive" reads to Faiz; affects decisions under Q105 framing. |
| **Q86 / Q91 / Q103** | Sub-agent recursion (10-deep cap) | SRS §3.4 generic delegation depth cap; no numeric value; no recursive-spawn primitive in architecture. | **OUTSIDE this audit's scope — covered in audit-02 §F-NRV-03.** |

---

## §6 Comparison — P20 Life Kernel vs Society Consciousness Loop Requirements

### §6.1 P20 Substrate (Reused)

| Capability | Source | State |
|---|---|---|
| 24/7 heartbeat (1s/10s/30s/60s/5m/1h) | `src/life_kernel/heartbeat.py` | LIVE |
| Decision-on-idle (60s graph.ainvoke) | `heartbeat.py` `_heartbeat_60s` | LIVE |
| 1h reflection + self-improvement candidates | `heartbeat.py` `_heartbeat_1h` + `self_improve.py` | LIVE |
| BackgroundCognition 6 loops (observer/memory/critic/curiosity/self_improvement/guardian) | `cognition.py` | SCAFFOLD (most are stubs awaiting LK-011 sensors) |
| HARD STOP global halt | `life_kernel:hard_stop` Redis key, <50ms trigger, AGENTS.md §0 V-008 | LIVE |
| WORM audit trail (`audit_writer` append-only) | P22.1 | LIVE |
| Per-agent `life_kernel:hard_stop` listener | `p24-fork-dependency.md` §5.2.1 | LIVE |
| World model (BDI beliefs + intentions + emotion-lite ledger) | `state.py` + `world_model` | LIVE |

### §6.2 What Society Must ADD Per Faiz Q62 (Advanced Beyond P20)

| Required Additive Capability | Status |
|---|---|
| **Continuous plan-generation loop** (intentions that aren't merely a reaction to accepted desire) | **MISSING** |
| **Dream cycle** (counterfactual replay, episodic re-narrative, low-cost generative reflection — NOT just consolidation) | **MISSING** |
| **24/7 awake-mode framing** at LLM-light cadence (5-min "active cognition heartbeat" — cheaper than LLM, more than liveness-ping) | **MISSING** (P20 5m cycle is a stub) |
| **Identity / aspiration layer** (Hermes has a self-story + a hypothesized future that supplies conversation topics) | **MISSING** |
| **Emotion / affect layer** (state + modulation + persona-bound expression) | **MISSING** |
| **Metrics for consciousness quality** (dream-cycle completion rate, plan-generation density, self-reflection depth, consciousness-loop budget, P20-vs-Society delta) | **MISSING** |
| **No-trigger long-horizon self-direction** (aspiration → subgoal → intention, vs 60s decision from current state) | **MISSING** |
| **Brutal research & brainstorming artifact** that addresses Faiz Q106 | **MISSING** |

### §6.3 Quantitative Comparison Sketch

(P20 baseline + Society_delta target — illustrative; not measured yet)

| Metric | P20 today | Society target (per Q62) |
|---|---|---|
| Self-reflect cadence | 1h | ≤30 min per Hermes (matches S3 component 6 already) |
| Plan-generation | None | Continuous cron-triggered + on-desire-triggered; ≥1/h |
| Dream cycle | None (consolidation only at 6h) | 4-6h; mixed consolidate + counterfactual replay + generative |
| Active cognition heartbeat | None (5m is stub) | 5m LLM-light ping |
| Conversation initiation | 60s decision-on-idle (graph decides "continue") | 60s + aspiration-driven topic proposal |
| Identity persistence | Manifest (system prompt + persona file + memory stream pinned) | Same + structured self-story block |
| Emotion | None | State-tracking + modulation in LLM-think layer |
| Metrics dashboards | heartbeat, HARD STOP, dashboard | All of P20 + consciousness-loop budget, dream-cycle rate, plan density, drift triad |

---

## §7 Detailed Gap Analysis (Brutal)

These are the **specific design decisions Faiz needs to make** before the Society can be called "more advanced than P20" per Q62.

### §7.1 Gap 1 — Plan-Generation Cycle is Reactive, Not Continuous

**Current state:** S3 §S3.2 component 8 "Plan generator" runs **only** when a new desire is accepted → triggers `policy(belief) -> action` (POMDP from P29 plan §P29-005). There is **no cron-triggered "what should I plan to do next hour / today / this week" loop**.

**Faiz's real ask:** Q57 "bisa bekerja, browsing, ngapain aja tanpa trigger apapun" requires the Society to **propose its own work** — not only respond to Faiz's signals. A Hermes without aspiration is a clocked reactor, not an agent.

**Design choices Faiz must approve:**

| Option | Description | Trade-offs |
|---|---|---|
| A | **Daily-plan cron** — every morning (per Hermes timezone), generate top-3 intentions for the day from aspirations; mirror Letta Generative Agents | Simple; loses emergent/dream-driven plans |
| B | **Drift-tracker-driven plan** — every reflection cycle (30min), if `provenance: reflection_cycle` beliefs suggest a goal, queue a desire | More emergent; needs reflection-quality gate |
| C | **Aspiration roster + weighted selector** — Hermes has `aspirations[]` with EWMA pull; cron samples weighted aspirations → desires → intentions | Best fit for Q39 (alive like humans) but adds identity/aspiration REQ |
| D | **Hybrid: A + C** — daily-plan behind aspiration roster | Recommended by research synthesis §7.2 (BDI+POMDP+Generative Agents stream) |

### §7.2 Gap 2 — Dream is Consolidation, Not Generative

**Current state:** P29 step 7: 6h cron, "episodic memory older than 7d compressed; semantic memory older than 30d pruned." This is **memory lifecycle management**, not dream.

**Faiz's real ask per Q76:** "Dreaming = memory consolidation + simulation + creative generation."

**Design choices Faiz must approve:**

| Option | Description | Trade-offs |
|---|---|---|
| A | **Keep consolidation**; add **counterfactual replay** sub-cycle: sample 5 random episodic memories → LLM-light: "what if X had gone differently?" → derive new beliefs tagged `provenance: counterfactual_dream` | Cheap LLM cost; novel-association generator |
| B | **Add episodic re-narrative**: agent reads own episodic stream → writes 1-paragraph "story of my last 24h" → stored as reflection | Memory-grounded identity; per Hermes init needed |
| C | **Add generative dream-journal**: during low/critical memory state, query Vector+FS for unrelated memories → LLM asks "what if these were connected?" → novel associations seeded into desires | True Q76 creative-generation; costliest |
| D | **Hybrid: A + C** at low LLM cost (use cheap model) | Recommended by Springdrift substrate pattern (research §16) |

### §7.3 Gap 3 — No Active Cognition Heartbeat (5m LLM-Light Ping)

**Current state:** P20 _heartbeat_5m is a stub. There's no lightweight signal that distinguishes "Hermes alive but idle" from "Hermes thinking" — an outside observer (Faiz or another Hermes) can only see heartbeat counters.

**Faiz's real ask per Q67 "without henti" (without stopping):** the Society should have a **visible, low-cost signal** that tells you it's awake and considering things.

**Design choice:** Add a `conscious_loop.pulse()` at 5m cadence that:
1. Reads `current_phase`, `last_goal`, `last_dream_cycle_at`, `last_reflection_at` from life-mind state.
2. Emits one lifecycle log line "thinking about X / about to dream / between reflections".
3. Updates the dashboard "conscience" widget.

This is **NOT an LLM call** — it's a structured-log read. Cost: ~0. Distinct from S5 metrics.

### §7.4 Gap 4 — Identity / Self-Story / Aspiration Layer Missing

**Current state:** Hermeses have a persona file (`SOUL.md`), a system prompt, a memory stream, and an audit trail. They do NOT have a **structured self-story block** answering "who am I? what am I for? what am I becoming?"

**Faiz's real ask per Q39 "talk like humans":** Conversation initiation must be **grounded in self**, not just in reaction. A Hermes without self-story can only respond to stimuli — never say "I was thinking about our project; here's a thought" unprompted.

**Design choices:** Introduce `agent_<id>.self_story` table (per Hermes, encrypted per §0.1/S4) with three sections:
- `identity`: pinned (3-5 sentences, hand-curated by founder/Hermes)
- `aspirations[]`: 3-7 long-arc goals with EWMA pull
- `current_project_focus`: 1-3 active projects, sourced from S3 desires

**Cost:** ~one new table per Hermes; one new REQ; one new ADR (or sync with P30/P33 if it lands first).

### §7.5 Gap 5 — Emotion / Affect Layer Missing

**Current state:** P29 introduces no emotion. Q52/Q105 are marked MISSING in audit-09.

**Faiz's real ask:** This is its own audit (cross-cut). It is critical to consciousness loop because emotion is **what makes a Hermes's curiosity/dream non-random**: emotion is a **mood-conditional weighting** over what to reflect on, what to dream about, what to aspire toward.

**Minimum viable design:** Vector of 6-8 primary affects (curiosity, concern, warmth, vigilance, irritation, satisfaction, resignation, anticipation), EWMA < 1.0 like relationship vectors. Updated:
- by LLM-self-report in 1h reflection (cheap)
- by POMDP transition (when an observation changes affect)
- by surveillance/sensor feed (Lk-011)
- by dreaming config (dream can perturb affect)

**Note**: PersonaSafetyPolicy requires **no per-Hermes emotional state in S3** (audit-04 §5.1.5 references SRS §3.4 line) — the audit notes this as a conflict. The resolution is: emotion lives in S4 (private, encrypted) — not in S3 (shared, default-deny). That preserves both invariants.

### §7.6 Gap 6 — Consciousness-Quality Metrics Absent

**Current state:** S13 dashboards list uptime / message rate / latency / heartbeat. Audit-02 §8.1.1.5: "No metrics for consciousness quality — observability dashboards in S13 list uptime / message rate / latency / heartbeat, but NOT dream-cycle completion rate, plan-generation density, self-reflection depth, or consciousness-loop budget."

**Faiz's real ask per Q62 "lebih tinggi speknya":** measure.

**Minimum viable design:** Add to S13 Grafana:
- `society_dream_cycle_completion_rate_per_hermes` (counter, rolling 7d)
- `society_plan_generation_density_per_hermes` (counter, rolling 24h)
- `society_self_reflection_depth_per_hermes` (avg derived-beliefs/cycle, rolling 7d)
- `society_consciousness_loop_budget` (LLM-tokens/day per Hermes; warn at >budget)
- `society_p20_delta_per_hermes` (Society self-eval score minus P20 baseline self-eval on identical probe set, monthly)

### §7.7 Gap 7 — No Brutal Research & Brainstorming Artifact

**Current state:** Zero. Audit-09 prompt-pack explicitly notes absence; audit-01 research-quality request explicitly unfulfilled.

**Faiz's real ask:** Q106 "perlu research dan brainstorming brutal."

**What brutal research must cover (next-step research wave, §9.1):**
- 2026 production consciousness-loop patterns beyond Letta (MemOS, Cognee, Memvid, Letta leaderboard, Hindsight)
- Hippocampal replay + counterfactual replay findings (deepmind context-engineering posts 2025-2026)
- Springdrift substrate patterns (`arXiv:2604.04660`) — runtime with **ambient self-perception (sensorium)**
- Autogenesis Protocol (`arXiv:2604.15034`) — `reflect → propose → verify` with deterministic verification
- VAGEN world-model RL (`ai.stanford.edu/blog/vagen/`)
- Multi-agent self-story / identity persistence patterns
- Affect modelling for LLM agents (Affective Computing 2025-2026; Plutchik + Russell circumplex + EWMA)
- Anethesiology of consciousness: Global Workspace Theory, IIT, predictive processing — what is each metaphor best for?
- Brutal brainstorming: explicit "we considered X, rejected because Y, picked Z" design log.

**What brutal brainstorming must produce (next-step brainstorm, §9.2):**
- **3-5 alternative consciousness-loop designs** with explicit pros/cons
- **Pick one + rejection rationale** for the alternative 4
- **Stack-ranking vs P20** with metrics + acceptance test
- **Implementation roadmap** — phase allocation (single phase? P29 + new step? new P29.5? merge into P35? new P37?)

---

## §8 Risks of NOT Doing This

If Phase 4 begins without consciousness-loop design:

1. **Implicit degradation (high)**. Implementation teams will inherit "P20 heartbeat + Letta reflection + S6 consolidation" as the loop by accident (per audit-02 §8.1.1 risk). The **Q62 explicit advance-beyond-P20 mandate** will be silently downgraded.
2. **Q62/Q67/Q106 unowned (high)** — no phase owns it; downstream SRS expansion will inherit the gap.
3. **Resource risk on 4C/16GB (medium)** — audit-06 R-008 does NOT cover the **consciousness-loop 24/7 on small hardware** scenario. If 24/7 means "every 30 min every Hermes LLM-light pings" with 4 Hermes, the LLM budget alone is non-trivial. **Brutal-research must answer**: what's the LLM-light cadence financially?
4. **Persona drift without identity (high)**. Failure mode: a Hermes with stable persona but no self-story cannot distinguish "I am becoming X" from "I was always X." This is a **Layered Mutability** violation in slow layer (persona) over time.
5. **Emotion-less dream produces infinite loops (medium)**. Without affect, dream cycle may produce uniformly-random novel beliefs. Affect-based weighting is one common fix (letting curiosity/connection-emotion drive dream selection).
6. **P20-delta not measurable (high)** — without metrics, you cannot claim Q62 "lebih tinggi speknya".

---

## §9 Recommended Research & Brainstorming Wave (Implements Q106)

### §9.1 Research Wave (recommended: spawn `librarian` sub-agent, output `external-consciousness-loop-research.md`)

**Scope:** 8-12 production/research sources, ≥80% from 2025-2026, totaling 30-60 KB.

| Source | Topic | Why |
|---|---|---|
| **Letta leaderboard + blog series (2026)** | Continuous consciousness loop with 4-tier memory + agent-self-orchestrated recall | Best production analog today; benchmark against Hermes spec |
| **MemOS (MemTensor)** | OS-style memory with explicit orchestration layer | Modern consciousness-loop substrate |
| **Cognee** | Knowledge-graph + memory with active cognition layer | Graph-anchored loop candidate |
| **Hindsight** (DEV.to "10 best memory layers 2026" review) | Memory substrate with agentic retrieval | Trend signal |
| **Springdrift (arXiv 2604.04660)** | Auditable persistent runtime for LLM agents; ambient self-perception (sensorium) pattern | Direct application to P20 heartbeat/world model per external-self-evolution-governance-research §16 |
| **Autogenesis Protocol (arXiv 2604.15034)** | `reflect → propose → verify` closed-loop operator with deterministic verification | Direct fit for P35 Ratchet; needs extension for society loop |
| **VAGEN (Stanford AI Lab 2026 blog)** | World-model RL — building internal world models via env interaction | Generative dream substrate candidate |
| **Anthropic context-engineering dream-cycle posts (2025-2026)** | Dream cycles as memory consolidation | Latest consciousness-loop framing from frontier lab |
| **Hippocampal-replay neuroscience (deepmind posts 2025-2026)** | Biological inspiration for offline dream cycle | Counterfactual-replay substrate |
| **Affective Computing 2025-2026** | Affect modelling + EWMA for LLM agents | Emotion layer substrate |
| **Global Workspace Theory (Baars; Dehaene)** | Cognitive architecture for consciousness | Brutal-brainstorm substrate option |
| **Predictive Processing / Free Energy Principle (Friston)** | Alternative consciousness substrate | Brutal-brainstorm substrate option |

**Deliverable:** `docs/setup-evidence/P28-P36-masterplan/research/external-consciousness-loop-research.md`. Produce within a single research wave; sibling to existing research files.

### §9.2 Brainstorming Wave (recommended: parent-led + librarian sub-agent, output `consciousness-loop-design-decisions.md`)

**Scope:** 5 alternative designs + 1 selected + rejection rationale for the other 4 + stack-ranking vs P20 + implementation roadmap.

**5 alternative substrate patterns:**

| Pattern | Inspiration | Trade-off |
|---|---|---|
| **A. Generative-Agents stream+reflect+plan** (Stanford 2023) | Already partly in S3 | Default; not advanced beyond P20 |
| **B. Letta 4-tier + sleep-time compute** | Letta; P20 sibling — no advance | Cancellation; not advanced |
| **C. Springdrift sensorium + 6-loop cognition** | Springdrift paper | **Best candidate for advance** — sensorium pattern is genuinely new |
| **D. Autogenesis reflect→propose→verify closed-loop** | Autogenesis paper | Strong for self-improvement; less for 24/7 continuous |
| **E. Global Workspace Theory (Baars)** | Neuroscience | Theoretically rich; engineering immature |

**Recommend: select C (Springdrift substrate + 6-loop P20 cognition + Letta 4-tier memory + Autogenesis verification) → reject A because not advanced beyond P20, reject B because already in P20, reject D because too mutation-heavy, reject E because engineering gap large.**

**Stack-ranking vs P20 (sketch):**

| Dimension | P20 | Society target | Delta metric |
|---|---|---|---|
| Heartbeat | 6 staged intervals | Same + 5m active cognition heartbeat | `society_active_cognition_pulse_rate` |
| Reflection | 1h, heuristic + ImprovementTracker candidate | 30 min, BDI-driven, EWMA decay | `society_reflection_density` |
| Consolidation | 6h episodic→semantic | Same + 4-6h counterfactual dream sub-cycle | `society_dream_cycle_count_per_week` |
| Plan generation | None | Hybrid cron daily + on-aspiration trigger | `society_plan_generation_density` |
| Active cognition signal | None (5m stub) | 5m pulse + dashboard | `society_consciousness_loop_completeness` |
| Identity | Persona + memory stream | + structured self-story block | `society_self_story_coherence_score` |
| Emotion | None | 6-8 affect EWMA, private | `society_affect_dynamic_range` |

**Implementation roadmap options:**

| Option | Description | Trade-off |
|---|---|---|
| α | **Bundle into P29 new step (P29-011)** — add self-story table, dream sub-cycle, plan cron, 5m pulse | Minimal scope change; one phase owns it |
| β | **New P37 — "Consciousness Loop Layer"** — own phase between P36 and the post-society phases | Cleanest; adds 2-3 weeks to timeline |
| γ | **Bundle into P36 (Production Hardening)** | Tight coupling with observability; risk-deliverable pile-up |
| δ | **Bundle into P35 (Self-Evolution)** | Couples consciousness with mutation — high risk of persona drift |

**Recommend option α (P29 new step) IF scope ≤10 steps; option β (P37) IF scope larger.** Final choice needs Faiz approval.

### §9.3 ADR-NN

After research + brainstorm, draft **ADR-066** (or next free number) for the consciousness-loop design decision. Mirror ADR-061 format. Lock in:
- Selected substrate pattern (recommend C from §9.2)
- Implementation roadmap option (recommend α conditional on scope)
- Metrics dashboards in S13
- Glossary term additions (consciousness loop, dreaming, self-story, aspirational plan)
- P20-vs-Society acceptance test (one Hermes running both; compare self-eval scores; Society strictly better)

---

## §10 Acceptance Criteria Mapping

Mapping §11 schema (AGENTS.md) to this audit's deliverables:

| AGENTS.md §11 Field | This Audit |
|---|---|
| What Was Done | Brutal gap audit of all 85 masterplan files for consciousness loop coverage |
| Files Changed | Audit only — zero masterplan files modified |
| Validation Results | 5 of 12 round-1 audits flag same finding; this audit triangulates |
| Evidence Artifacts | This report: `audit-14-consciousness-loop-gap.md` |
| Doc-Sync Impact | Recommend three follow-ups: (a) external-consciousness-loop-research.md; (b) consciousness-loop-design-decisions.md; (c) ADR-NN |
| Boundary Compliance | PersonaSafetyPolicy Y4/Y5 preserved (no Y6 path); consent not bypassed; HARD STOP preserved; no intimate data leakage introduced by this audit. |
| Rollback/Re-run Safety | This audit edits nothing; follow-up wave is independent and idempotent |
| Design Decisions/Caveats | None owned by this audit; §9 lists 7 design choices Faiz must approve |
| Auditor Gate | This audit gates §9 wave before phase-4 expansion; |
| Security Scan | No PII / surveillance data / secrets introduced |
| Acceptance Criteria Mapping | Q39/Q57/Q62/Q67/Q76/Q106/Q108 (and Q52/Q105 cross-cut) — see §5 |
| Footer | At end |

---

## §11 Cross-References

| Reference | Use |
|---|---|
| `audit-01-research-quality.md` §6 | Confirms consciousness-loop research gap |
| `audit-02-architecture.md` §8.1.1 F-NRV-01 | CRITICAL FAIL with 5 detailed gaps |
| `audit-02-architecture.md` §5 (line 200) | Notes that S6 6h consolidation is Q108-PASS but NOT Q67 composite |
| `audit-03-brd-prd.md` §4.3 | 30% vision reflection rate; consciousness loop naming absent |
| `audit-04-srs-fsd.md` §5.1.1 | Q67 NEEDS-REVIEW with proposed REQ-NN text |
| `audit-05-tdd-rtm.md` §5 | Substrate present distributed across C1+C2+C3+C5 |
| `audit-06-acceptance-risk-glossary.md` GL-FINDING-01..03 + R-016 | Glossary + R-008 needs loop-specific risk |
| `audit-07-adr.md` §5 | ADR deferral record; #13/#14/#15 target ADR-NN |
| `audit-08-roadmap.md` §4.1 | Roadmap ownership mapping; consciousness loop unowned |
| `audit-09-prompt-pack.md` §4.1 | Critical-topic scoreboard: Q62/Q67/Q106 MISSING |
| `audit-13-per-phase-plans.md` §6.1 | P29 semantic-PASS on Q67 (BDI+POMDP) but partial on Q76/Q108 |
| `src/life_kernel/heartbeat.py` §_heartbeat_60s | Decision-on-idle mechanism exists |
| `src/life_kernel/cognition.py` §BackgroundCognition | 6-loop scaffold; most are stubs |
| `architecture/hermes-society-master-architecture.md` §S3.2 component 6/8 | Plan generator + Reflection generator references |
| `architecture/architecture-s1-s5-runtime-memory.md` §S3.2 item 6 | Reflection loop pattern |
| `research/memory-world-model.md` §2.4 | Generative Agents paradigm (close analog to P20) |
| `research/synthesis-external-architecture.md` §4.3, §7.2 | BDI+POMDP+Generative Agents design synthesis |
| `research/external-self-evolution-governance-research.md` §16-§17 | Springdrift + Autogenesis adoption hints |
| `qa-inputs/Guinevere_QA_Answers_Samm.md` line 39 | "Guinevere selalu available — tidak istirahat secara teknis" |

---

## §12 Acknowledged Limitations

1. **I did not touch the masterplan files** — this audit is observational only.
2. **The L60s decision-on-idle mechanism** from P20 heartbeat is **REUSED** but its semantics ("what 'continue' means") are graph-state-dependent and not explored in depth here.
3. **The "Letta-style" S3 reflection loop** (every 30 min per Hermes) **was not re-read in code** because no Hermes-specific BDI implementation has been written yet. Audit-13 §6.1 confirms the architectural existence but P29's exit-criteria includes 24h soak test which is post-implementation.
4. **The dream-cycle's exact LLM cost** is **not estimated**. Required for §6 R-008 expansion.
5. **The Q39/Q52/Q105 cross-cuts** are flagged but not fully evidenced here — they belong to their own audits.

---

## §13 Final Verdict + Next Action

**VERDICT: FAIL.** Multiple independent auditors (audit-01, audit-02, audit-03, audit-04, audit-06, audit-08, audit-09, audit-13) converge on the same finding: the substrate is real but the **first-class consciousness-loop primitive — 24/7 self-reflect+plan+dream, more advanced than P20, with identity/aspiration/emotion/metrics — is NOT designed and NOT researched.** This audit documents the seven concrete design choices (§7) that Faiz must approve before Phase 4 SRS/FSD expansion begins.

**Recommended next action (in order):**

1. **Spawn research wave** (§9.1): output `external-consciousness-loop-research.md` (30-60 KB, ≥8 sources).
2. **Spawn brainstorming wave** (§9.2): output `consciousness-loop-design-decisions.md` (alternative designs + stack-ranking + roadmap option).
3. **Draft ADR-NN** (§9.3): mirror ADR-061 format, lock substrate pattern + metrics + glossary.
4. **Update round-2 audits** with research + design decisions:
   - audit-01 (research-quality) — round 2 mark consciousness-loop PASS.
   - audit-02 (architecture) — round 2 mark F-NRV-01 fixed.
   - audit-04 (SRS/FSD) — round 2 add REQ-NN.
   - audit-06 (acceptance-risk-glossary) — round 2 add glossary + R-016.
   - audit-08 (roadmap) — round 2 mark ownership.
   - audit-09 (prompt-pack) — round 2 add consciousness-loop-design prompt.
5. **Approve implementation** in target phase (recommend P29 new step OR new P37) **before** Phase 4 SRS/FSD expansion begins.

**No masterplan file is edited by this audit. It is observational and prescriptive for the follow-up wave.**

---

## Footer

Version 1.0 | 2026-06-28 | Author: Guinevere (parent agent)

| Entity | Session |
|---|---|
| Trigger | Faiz Q106 in `qa-inputs/prompt-pack.md` (audit-09 §4.1 item 1) + Q62 / Q67 / Q76 / Q108 / Q57 / Q39 |
| Cross-cuts | Q52 / Q105 / Q83 / Q86 / Q91 / Q103 (raised with cross-reference; not fully evidenced in this audit) |
| Owner | Guinevere (parent) for follow-up wave |
| Reviewer | TBD (Oracle or Faiz) |
| Required before | Phase 4 ADR-NN + SRS/FSD expansion |
