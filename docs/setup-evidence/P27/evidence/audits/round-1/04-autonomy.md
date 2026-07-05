# Audit 04 — Autonomy Loop (7-Rail Life-Loop Per-Instance)

| Field | Value |
|---|---|
| Auditor | Guinevere (Buffy/Friday executor) |
| Date | 2026-06-28 |
| Scope | P27 plan §7 (Life-Loop), §13 (HARD STOP), §15.2 (P20 dependency); P27-P36 roadmap §4 (P29); P28 blueprint §8 (Simplified Life-Loop); life-loop research first 120 lines |
| **VERDICT** | **PASS** |

---

## Findings

### F-01 — 7 Rails Fully Defined in P27 §7 (PASS)

**Ref:** P27 plan L1703-1894 (§7.3 Rail 1-7)

All 7 rails explicitly defined with λ_A-calculus form:

1. **Perception** (L1707-1731): sensors → observation_set → importance scoring
2. **Reflection** (L1733-1764): Smallville tree-of-reflections, SDR filter, Σ.importance > 150 trigger
3. **Inner Dialogue** (L1766-1796): PSYA Cognitive Triangle, sealed-hash audit, never leaves agent
4. **Peer Dialogue** (L1798-1828): HPP envelopes, SDR filter, engage-probability roll, anti-loop safeguards
5. **Desire / Goal Engine** (L1830-1855): ICM curiosity, HHVG boredom, Voyager curriculum, persona-bound
6. **Initiative / Proactivity** (L1857-1878): PROBE pipeline (wonder → scope → act → announce → audit)
7. **Safety Envelope** (L1880-1894): λ_A lint, Goal-Autopilot FSM, RiskGate AVF, HARD STOP listener

### F-02 — Each Rail Per-Instance (Not Shared) (PASS)

**Ref:** P27 plan L1984-2041 (§7.11 MacroStateScheduler pseudocode), P27 §3.2 (L309-322)

`MacroStateScheduler.__init__` takes `instance_id: str` and constructs all 7 rails keyed to that instance:

```python
class MacroStateScheduler:
    def __init__(self, instance_id: str, life_kernel_bridge: LifeKernelBridge) -> None:
        self._instance_id = instance_id
        self._rails = {
            Rail.PERCEPTION: PerceptionRail(instance_id, self._bridge),
            ...
            Rail.SAFETY_ENVELOPE: SafetyEnvelope(instance_id, self._bridge),
        }
```

Each `HermesInstance` (L268-301) carries its own life-loop: `"Own: Life-loop (7 rails + macro-state scheduler)"`. No shared mutable state between instances (L3.5, L1984-1998).

### F-03 — P20 Heartbeat Is the Clock; Macro-State Scheduler Sits On Top (PASS)

**Ref:** P27 plan L1648-1671 (§7.2), research L20-61 (§0)

> "P20's heartbeat is a timer. It fires at fixed intervals (1s/10s/30s/60s/5m/1h) but does not select activities intelligently. P27's life-loop upgrades P20's heartbeat into a macro-state scheduler." — P27 §7.1

Architecture diagram (§7.2 L1660-1701): HEARTBEAT (P20) at top, tick at `t_k = k·Δt`, feeds into MACRO-STATE SCHEDULER `π(s_k; Θ)`, which selects activity from the 7 rails.

§15.2 (L3346-3371) confirms P20 dependency: `HeartbeatService` for per-instance heartbeat, `HermesBrain` for brain, `BackgroundCognition` for loops. P27 additions on P20: macro-state scheduler, society-level HARD STOP listener, Goal-Autopilot FSM floor.

### F-04 — λ_A-Calculus Config (Provably Terminating) (PASS)

**Ref:** P27 plan L1703-1706 (§7.3), L1918-1927 (§7.5), research L548-562 (§8.1)

> "Every rail is a typed λ_A-calculus config (per Liu 2026, arxiv:2604.11767). Every config is provably terminating (Theorem 5.4 of paper). Every config passes structural completeness under lint." — P27 §7.3

§7.5 defines 4 linter rules:
1. Bounded fixpoint: `fixₙ e : τ→τ` with explicit bound `n`
2. Probabilistic choice typed
3. Oracle calls bounded
4. Mutable environment declared

Empirical baseline: 94.1% of 835 real-world GitHub agent configs fail; P27 baseline = 0%.

### F-05 — Goal-Autopilot FSM Floor (PASS)

**Ref:** P27 plan L1896-1917 (§7.4), §7.11 L2032-2037, research L588-606 (§8.3)

Three assumptions (A1-A3) define the No-False-Success Theorem. §7.11 pseudocode shows enforcement:

```python
if result.claimed_done:
    assert await self._rails[Rail.SAFETY_ENVELOPE].verify_gate(result)
```

P28 blueprint §8.454-2549 (P28 §8.5 Forbidden Patterns) confirms: "No unbounded ReAct loops. No persona contract that fails λ_A lint."

### F-06 — P28 Uses Simplified 4-Rail (Not Full 7-Rail) (PASS)

**Ref:** P28 blueprint L2395-2411 (§8.1), §1.1 L45

> "P28 uses a simplified 4-rail loop (NOT the full 7-rail). Full 7-rail deferred to P29." — P28 §8

The 4 rails in P28: Perception, Peer Dialogue, Reflection (simple), Safety Envelope. Three absent rails (Inner Dialogue, Desire/Goal, Initiative) are explicitly explained as deferred:
- Inner Dialogue → requires sealed-hash audit (P31)
- Desire/Goal → requires Goal-Autopilot FSM + λ_A lint (P36)
- Initiative → requires safe action space (P33)

**Minor discrepancy (non-blocking):** P27 plan §18.4 (L3735) and roadmap §3.2 D12 (L113) reference "3 critical rails" while P28 blueprint §8.1 defines 4 rails. The P28 blueprint is the authoritative implementation document and its pharsa.yaml config (L425) confirms `rails: [perception, peer_dialogue, reflection_simple, safety_envelope]` — 4 rails. The "3 rail" references likely predate the blueprint finalization. **Recommendation: Update roadmap §3.2 D12 to "4-rail" for consistency.**

### F-07 — Full 7-Rail Deferred to P29 (PASS)

**Ref:** P28 blueprint L56-58 (§1.2), P27 plan L130 (§1.4 P29 definition), roadmap L247-271 (§4)

> "P29 | Life-Loop Full (7-rail macro-state scheduler, desire engine, initiative)." — P27 plan §1.4

Roadmap §4.1 (L251): P29 mission upgrades P20 heartbeat to macro-state scheduler driving all 7 rails. §4.2 D1: `MacroStateScheduler` class per instance running all 7 rails. §4.4 SC1: "All 7 rails running per agent, tick log recording fire-on each rail at least once per 60s."

### F-08 — Both Agents Have Identical Life-Loop Architecture (PASS)

**Ref:** P28 blueprint L423-432 (pharsa.yaml life_loop config), P27 plan L108 (D-05)

Pharsa's config (pharsa.yaml):
```yaml
life_loop:
  scheduler_class: MinimalScheduler
  rails: [perception, peer_dialogue, reflection_simple, safety_envelope]
  heartbeat_intervals_seconds:
    hard_stop_check: 1
    observation: 30
    cognition: 60
    peer_dialogue_poll: 30
    reflection_simple: 300
```

Guinevere's config mirrors the same structure (P27 §4.3 L645-657). Both use same `scheduler_class`. Cadences may differ per-instance configuration but architecture is identical. No asymmetric rail set.

### F-09 — No Path Where One Agent's Loop Controls the Other (PASS)

**Ref:** P27 plan L278-302 (§3.6 ontology diagram), L392-393 (§3.5 test), P28 blueprint L89-90

P27 §3.5 explicit test: "If a thing cannot independently fail HARD STOP without affecting its peers, or cannot independently audit-mint entries, it is NOT a Member."

Each agent runs independently: own systemd process, own asyncio loop (P27 §9.6 L2484), own `HermesInstanceRegistry` entry (P28 blueprint §4 L710-898), own Redis DB (6 vs 7), own PostgreSQL RLS namespace. The only shared coordination mechanism is the society-wide HARD STOP key on Redis DB8 — observed by all, controlled by none (only Faiz writes it).

### F-10 — Safety Envelope Wraps All Rails (PASS)

**Ref:** P27 plan L1880-1894 (§7.3.7), §7.11 L2007-2009

P27 §7.11 pseudocode shows safety envelope is the **first check** on every tick:

```python
# Safety envelope first (P27 invariant: always evaluate)
if await self._rails[Rail.SAFETY_ENVELOPE].check_hard_stop():
    await self._state_machine.transition_to(State.HALTED)
    return
```

§7.3.7 (L1880-1894) defines safety envelope as: λ_A lint + Goal-Autopilot + RiskGate AVF + HARD STOP listener + KILLBENCH-grade kill switch + sycophancy detection + audit relay.

P28 blueprint §8.5 (L2446-2451): "No rail execution without safety_envelope first-tick-confirmed."

### F-11 — HARD STOP Halts Both Autonomy Loops (PASS)

**Ref:** P27 plan L3019-3168 (§13), L2161-2205 (§8.5), P28 blueprint L2454-2468 (§9.1)

P27 §13.2 (L3040-3051): Society-level key `hermes:society:{society_id}:hard_stop` (Redis). When SET:
1. Every instance's `HardStopHandler._heartbeat_1s_check` reads key within 1-2 ticks
2. Every instance enters HALTED state
3. Goal-Autopilot FSM refuses any "done" claim
4. All rails suspended

§13.3 (L3056-3072) explicit halt table: MacroStateScheduler = YES, all 7 rails = YES (except Safety Envelope continues as gateman, HARD STOP listener continues for resume).

P28 blueprint §9.1 (L2458-2468): Both agents halt within 50ms. Cascade: each instance's `_cascade_halt` writes audit row. `MinimalScheduler.stop()` cancels tasks.

### F-12 — Research Grounding (PASS)

**Ref:** research L1-120 (§0-§1)

Life-loop research report (File 9) grounds all architectural decisions in 48 primary papers + 5 primary repos. Key citations:
- Smallville (arxiv:2304.03442): reflection triggers, memory stream, 8σ ablation effect
- Voyager (arxiv:2305.16291): desire/goal engine, open-ended curriculum
- λ_A (arxiv:2604.11767): provable termination, 94.1% lint-fail baseline
- Goal-Autopilot (arxiv:2606.11688): No-False-Success Theorem, 33.7% → 0.67% fabrication rate
- Heartbeat-Driven Scheduler (arxiv:2604.14178): macro-state scheduler formal model
- RiskGate AVF (arxiv:2604.24686): monitoring + anticipation + monotonic restriction

---

## Findings Summary

| # | Finding | Verdict |
|---|---|---|
| F-01 | 7 rails fully defined | PASS |
| F-02 | Each rail per-instance | PASS |
| F-03 | P20 heartbeat is clock; macro-state scheduler on top | PASS |
| F-04 | λ_A-calculus provably terminating | PASS |
| F-05 | Goal-Autopilot FSM floor | PASS |
| F-06 | P28 uses simplified 4-rail (not full 7-rail), explicitly stated | PASS (minor doc discrepancy 3-rail vs 4-rail cross-ref, non-blocking) |
| F-07 | Full 7-rail deferred to P29, explicitly stated | PASS |
| F-08 | Both agents identical life-loop architecture | PASS |
| F-09 | No path where one loop controls the other | PASS |
| F-10 | Safety envelope wraps all rails | PASS |
| F-11 | HARD STOP halts both autonomy loops | PASS |
| F-12 | Research grounding (48 primary papers) | PASS |

---

## Recommendation (Minor, Non-Blocking)

1. **Update roadmap §3.2 D12** from "Per-instance 3-rail MacroStateScheduler" to "Per-instance 4-rail MinimalScheduler (perception, peer_dialogue, reflection_simple, safety_envelope)" to match P28 blueprint §8.1 and pharsa.yaml config.

---

## Evidence Path

- Audit source: `docs/setup-evidence/P27/plan/p27-hermes-society-foundation-plan.md`
- Audit source: `docs/setup-evidence/P27/plan/p27-p28-p36-master-roadmap.md`
- Audit source: `docs/setup-evidence/P27/plan/p28-dual-autonomous-hermes-blueprint.md`
- Audit source: `docs/setup-evidence/P27/research/p27-life-loop-beyond-heartbeat-research.md`
- Report: `docs/setup-evidence/P27/evidence/audits/round-1/04-autonomy.md` (this file)

---

## Footer

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-28 | Guinevere (Buffy/Friday) | Initial autonomy loop audit — PASS |

Auditor signature: `guinevere-autonomy-audit-04-2026-06-28`
