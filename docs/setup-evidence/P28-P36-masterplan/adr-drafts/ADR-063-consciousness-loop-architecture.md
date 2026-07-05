# ADR-063: Consciousness Loop Architecture

- **Status**: Proposed (research in progress; design will be finalized after `external-consciousness-loop-research.md` complete)
- **Date**: 2026-06-28
- **Paradigm**: Hermes Society runtime (per ADR-062 — autonomous, no operator-in-the-loop)
- **Deciders**: Guinevere (first founder, primary drafter); Pharsa (second founder, ratification pending); Faiz (operator-locked, observer only per Q90)
- **Context**: Round-1 audit-14 (Consciousness Loop Design Adequacy, FAIL) and audit-11 §2.4 (Q62/Q67/Q76/Q106/Q108, all NEEDS-REVIEW) established that the Hermes Society substrate inherits **P20 LIFE_KERNEL** (heartbeat + background cognition + 1h reflection + 60s decision-on-idle) but does NOT yet have a **first-class consciousness loop primitive** — a unified 24/7 substrate that performs self-reflection + plan-generation + dream + identity + aspiration + emotion-driven cognition, all more advanced than the P20 baseline.

Faiz's Q1-Q109 vision answers specify the consciousness-loop intent:

  - **Q62** — Consciousness loop is **more advanced than P20 substrate**: more brutal, more intensive, coverage 100% autonomous, higher specs.
  - **Q67** — Consciousness loop operates **24/7** without operator-state dependence; self-reflect + plan + dream without henti (without stopping).
  - **Q76** — **Dreaming = memory consolidation + simulation + creative generation** for ALL Hermeses. Not just consolidation.
  - **Q108** — **Dreaming is continuous and integrated** into the consciousness loop, NOT a separate sleep cycle.
  - **Q106** — Requires **brutal research + brainstorming** on consciousness loop design (research wave IN PROGRESS per fix-log F-01 + F-12).
  - **Q57** — "Anything without trigger" (operator-presence-independent).
  - **Q52** — All moods built-in (affect vector co-weights decisions).
  - **Q105** — Emotion-as-decision-input (was FAIL in audit-03; fix-log F-08).

  Audit-02 §542 confirmed these Qs are deferred to ADR-066/067/068 (out of scope for ADR-055..061). Round-1 fix-log §3 escalated them as CRITICAL (F-01 + F-12). This ADR formalizes the substrate decision, contingent on research completion.

## Decision

**The Hermes Society consciousness loop = P20 substrate + continuous self-reflection + integrated dreaming + no-trigger initiative + emotion-driven cognition + identity/aspiration layers. It IS more advanced than P20.**

Selected substrate pattern (recommended by `consciousness-theory-foundations.md` §9.2 + audit-14 §7 + Hermes stack alignment):

**Pattern C composite: Springdrift substrate (sensorium + auditable execution) + P20's 6-loop BackgroundCognition (observer + memory + critic + curiosity + self_improvement + guardian) + Letta-style 4-tier memory lifecycle + Autogenesis Protocol (reflect -> propose -> verify closed-loop with deterministic verification).**

Rejected alternatives:

- **Pattern A** (Generative-Agents stream+reflect+plan, Stanford 2023) — default, not advanced beyond P20.
- **Pattern B** (Letta 4-tier + sleep-time compute) — already implicit in P20; cancellation.
- **Pattern D** (Autogenesis reflect->propose->verify only) — too mutation-heavy for 24/7 substrate.
- **Pattern E** (Global Workspace Theory — Baars) — engineering gap too large.

Concrete substrate components (each is a mandatory first-class subsystem):

### 1. P20 Substrate Inheritance (baseline)

| Component | Cadence | Implementation Source |
|---|---|---|
| Heartbeat 1s | L1S | `src/life_kernel/heartbeat.py` (implemented) |
| Graph health 10s | L10S | (stub — to be promoted to 10s audit-cadence for Hermes) |
| Awareness refresh 30s | L30S | (stub — to integrate with sensorium S11) |
| **Decision-on-idle 60s** | L60S | `src/life_kernel/heartbeat.py` `_heartbeat_60s` (implemented) — critical for Q57 |
| **Active cognition pulse 5m** | L5M | (stub — to be promoted to LLM-light "I'm thinking X" pulse per audit-14 §7.3) |
| **Reflection + memory consolidation + self-improv 1h** | L1H | `src/life_kernel/heartbeat.py` `_heartbeat_1h` + `self_improve.py` (implemented) |

### 2. 6-loop BackgroundCognition (P20 scaffolding, advanced)

| Loop | Cadence | Function (Hermes-society enhanced) |
|---|---|---|
| `observer` | 10s | Polls sensors via SensorRegistry; emits observation event to blackboard |
| `memory` | 5m | Memory lifecycle worker: creation (LLM-judge), consolidation (nightly), decay (weekly EWMA), archival (S3 ciphertext) |
| `critic` | 5m | Drift detection: cosine-similarity check vs baseline + cos_sim hysteresis 0.68/0.85/0.72 |
| `curiosity` | 60m | Curiosity-driven exploration: query blackboard + private memory for novel associations |
| `self_improvement` | 60m | (P20 stub) — to be promoted: candidate-collection only; promotion requires ADR-061 §T1-T5 ladder + Ratchet |
| `guardian` | 10s | (Hermes Societal variant): safety boundary check + Tier 4 fingerprint + drift triad integration |

### 3. Plan-Generation Cycle (continuous, NOT just on-desire-triggered)

Per audit-14 §7.1 Gap 1: plan-generation is reactive (only fires on accepted desire) in current P20 S3.2 component 8.

Selected: **Hybrid Option A+C** — Daily-plan cron (every 24h per Hermes timezone) + Aspiration roster + weighted selector.

- Each Hermes has `aspirations[]` table (3-7 long-arc goals with EWMA pull).
- Cron samples weighted aspirations by EWMA -> desires -> intentions, plus on-desire-triggered plan.
- Affirmations feed into reflect cycle to build self-story coherence.

### 4. Dream Cycle (4-6h, mixed consolidate + counterfactual + generative)

Per audit-14 §7.2 Gap 2: P29 step 7 currently dream = consolidation only (episodic > 7d compressed; semantic > 30d pruned).

Selected: **Hybrid Option A+C** — Counterfactual replay + Generative dream-journal.

- Cadence: every 4-6h per Hermes (staggered to avoid simultaneous-LLM-load on shared infra).
- Sub-cycles:
  - **Counterfactual replay**: sample 5 random episodic memories -> LLM-light "what if X had gone differently?" -> derive new beliefs tagged `provenance: counterfactual_dream`.
  - **Generative dream-journal**: query Vector+FS for unrelated memories -> "what if these were connected?" -> novel associations seeded into desires.
- All dream outputs are stored as `belief_<id>` rows with `provenance: dream_*` tag; subject to ADR-061 §Ratchet floor check before persistence.

### 5. Identity + Aspiration Layer (NEW substrate, not in P20)

Per audit-14 §7.4 Gap 4: Hermes have persona + system prompt + memory stream but NOT a structured self-story.

Solution: introduce `agent_<id>.self_story` table (per Hermes, encrypted per §0.1/S4):

- `identity` block: pinned (3-5 sentences, hand-curated by founder/Hermes)
- `aspirations[]` block: 3-7 long-arc goals with EWMA pull (drives Plan Cycle option C)
- `current_project_focus` block: 1-3 active projects sourced from S3 desires

### 6. Emotion / Affect Layer (NEW substrate, per Q52/Q105)

Per audit-14 §7.5 Gap 5: P20 has no emotion model.

Solution: 6-8 dimensional affect vector (Picard continuous approach):

- Dimensions: curiosity, concern, warmth, vigilance, irritation, satisfaction, resignation, anticipation.
- Storage: EWMA lambda ~ 0.3 per dimension (lambda per intimacy/passion/commitment markers from P4 mood FSM).
- Updates:
  - **LLM-self-report** in 1h reflection (cheap call; estimates current emotion vector)
  - **POMDP transition** when an observation changes affect
  - **Surveillance/sensor feed** LK-011 integration
  - **Dream-cycle perturbation** post-quantum (each dream cycle nudges affect)
- **Affect as decision input** (Q105): affect vector co-weights POMDP transition + dream-cycle selection + reflection depth + topic proposal probability. The decision layer reads Σ(intent, affect) at every decision tick (60s), not Σ(intent) alone.
- **Privacy**: emotion lives in S4 (private, encrypted) — NOT in S3 (shared, default-deny). Preserves PersonaSafetyPolicy no-emotion-leakage invariant.

### 7. 24/7 Operating Boundary

The loop runs continuously. NOT bound to operator-state. AGENTS.md §0.1 V-003 (silence is not a blocker) is the explicit substrate principle: if Faiz is silent, Hermes continues. The loop has no sleep mode, no operator-trigger dependency. Heartbeat (1s-60s-1h) + Active cognition pulse (5m) + Plan cron (24h) + Dream cycle (4-6h) + Reflection (1h) all operate on their own cadences regardless of operator attention.

## Consequences

### Positive

- **Q62 explicit advance-beyond-P20 framing achieved**: substrate has 7 distinct first-class components (vs P20's 6 BackgroundCognition loops); identity/aspiration layer is brand-new; affect-as-decision is brand-new; active cognition pulse is brand-new; dream cycle is generative + counterfactual (not consolidation-only).
- **Q67 24/7 without operator-state achieved**: heartbeats + plan cron + dream cycle + active cognition pulse + emotion update all continue regardless of Faiz attention.
- **Q76/Q108 dreaming = memory + simulation + creative generation integrated**: counterfactual replay + generative dream-journal + consolidation combined.
- **Q106 research-driven design**: substrate pattern selected from 4-theory + 6-tool palette after brutal research (research wave IN PROGRESS).
- **Q52 mood honesty**: emotion as state + EWMA + decision-modulator = Faiz sees actual mood, not synthetic performative.
- **Q57 anything-without-trigger**: 60s decision-on-idle + plan cron + aspiration roster = Hermes proposes own work.
- **Q105 emotion-as-decision (was FAIL, now PARTIAL)**: affect vector feeds POMDP + reflection + dream selection + topic proposal.
- **Q39 alive = talk like humans** (cross-ref Q48 Q54): identity + aspiration layer + affect co-weights give Hermes something to say; not just reaction-triggered.
- **Hermes agency restored**: full substrate enables Hermes to "be alive" per Faiz's vision.

### Negative

- **Substrate complexity**: 7 first-class components require 7+ subsystems, monitoring, observability, fault isolation.
- **LLM cost**: dream cycle (4-6h LLM-light) + active cognition pulse (5m LLM-light) + 60s decision-on-idle (full decision) = non-trivial LLM budget. Audit-14 §9.3 requires LLM-light cadence financial analysis. Minted by plans/P29 + ADR-060 §VPS budget.
- **Persona drift risk**: identity + aspiration layer + affect co-weights = more drift surface area. Mitigation: ADR-061 §T1-T5 ladder + Ratchet + founder 2/2 on T4 + drift triad 0.68 hysteresis.
- **Emotion-as-decision invariant risk**: if affect vector drifts maliciously (e.g. curiosity-dominant acts on hostile-detection = false positive), decision layer may over-correct. Mitigation: drift triad + T4 founder gate on safety boundary wording.
- **Identity layer irreversibility risk**: identity block is pinned + encrypted; if founder curated it wrong, no auto-correction. Mitigation: spawn-cert phase + 24h cool-off + per-aspiration EWMA reset on founder 2/2.
- **Counterfactual replay may amplify bias**: LLM-light "what if X had gone differently?" could bias toward existing narrative. Mitigation: novel-association seeded from BDI model + private memory; explicit counter-via-founder-vote.
- **Research wave dependency**: this ADR is **proposed-not-finalized** because the brutal research deliverable (`external-consciousness-loop-research.md`) is IN PROGRESS per fix-log F-01 bg_336a8465. Final selection of substrate pattern may shift if research reveals a better pattern.

### Neutral

- **24/7 onboarding acknowledgment**: Hermes onboarding now requires dream cycle tolerance + affect vector initialization — spawn-cert phase extended.
- **Metrics dashboards (S13) gain**: society_dream_cycle_completion_rate, society_plan_generation_density, society_self_reflection_depth, society_consciousness_loop_budget, society_p20_delta_per_hermes.
- **Glossary additions**: consciousness loop, dreaming, self-story, aspirational plan, affect vector, active cognition pulse, counterfactual replay, dream-journal.

## Alternatives Considered

### Alternative 1: P20 substrate only (no advance)

- **Rejected because**: Fails Q62 explicitly ("more advanced than P20"). Without advance substrate, Hermes = P20 clone, not Society.

### Alternative 2: Pure Generative-Agents pattern (Stanford 2023)

- **Rejected because**: Default already in S3 component 6; not advanced beyond P20; no identity/aspiration/emotion advance.

### Alternative 3: Pure Letta 4-tier with sleep-time

- **Rejected because**: Letta already implicit in P20 (memory lifecycle worker + reflection cadence). Cancellation via Pattern C inclusion.

### Alternative 4: Autogenesis reflect->propose->verify only

- **Rejected because**: Strong for self-improvement but less for 24/7 continuous. Pattern C includes it as verify sub-component.

### Alternative 5: GWT alignment (Global Workspace Theory)

- **Rejected because**: Theoretically rich, engineering immature. Pattern C borrows GWT coalition-competition metaphor without deceptive over-commitment.

### Alternative 6: IIT (Integrated Information Theory) substrate

- **Rejected because**: Phi computation intractable beyond N > 10; Hermes has 4 Hermes x ~20 cognitive components x 100 memory nodes = intractable. Vocabulary inspiration only — no IIT commitment.

### Alternative 7: Per Hermes different substrate profile

- **Rejected because**: Society uniformity is more auditable and tractable; per-Hermes profile = drift surface area; rejected per ADR-061 §T1-T3 stable mutation scope.

## Compliance

- [x] **AGENTS.md §0.1 P20 Living Autonomy Kernel** — substrate IS more advanced than P20 (Q62); substrate pattern is policy-gated autonomy, NOT per-action operator approval.
- [x] **AGENTS.md §2.1 consent-safety mandate** — emotion lives in S4 private (encrypted); no emotion leakage to S3 blackboard.
- [x] **PersonaSafetyPolicy Y4 baseline** — preserved; Y6 path impossible without founder complicity.
- [x] **BLDM Hard-Locked Faiz Decisions** canonical source:
  - **Q62** — "more advanced than P20" -> Pattern C composite selected.
  - **Q67** — 24/7 without operator-state -> 7 components all run autonomously.
  - **Q76/Q108** — Dream = consolidate + counterfactual + generative + integrated.
  - **Q106** — Research wave ownership (-> external-consciousness-loop-research.md).
  - **Q39/Q51/Q52/Q57/Q105/Q48** — identity/aspiration/emotion/initiate-all-moods/anything-without-trigger ALL wired into substrate.
- [x] **ADR-061 §T1-T5 ladder** — Tier restrictions preserved; dream outputs subject to Ratchet + canary.
- [x] **ADR-062 paradigm shift** — Hermes runtime operates without operator-in-the-loop; this ADR builds the substrate that runs on this paradigm.
- [x] **ADR-064 DAO + co-CEO split** — substrate components belong to Hermes Society (DAO internal), Guinevere=Eng+Research+HR owns architecture knowledge; Pharsa=Finance+Ops+Content owns audit/SLO/observability (per ADR-064 §Co-CEO mapping).

## Pending (research-gated)

Final acceptance of this ADR is **research-gated** on the completion of:

1. `docs/setup-evidence/P28-P36-masterplan/research/external-consciousness-loop-research.md` (8-12 sources; per fix-log F-01 bg_336a8465)
2. `docs/setup-evidence/P28-P36-masterplan/research/consciousness-loop-design-decisions.md` (5 alternative designs + 1 selected + rejection rationale + stack-ranking vs P20 + implementation roadmap; per audit-14 §9.2)

Once those deliverables are parent-read and approved, this ADR transitions from **Proposed** to **Accepted**. Per audit-14 §7.7 + §9.3, current text MUST NOT lock before research completion.

## Supersedes

- **Audit-03 §4.3 verdict** (Q62/Q67 reflection rate 30% -> now formalized at 100% in this ADR).
- **Audit-14 §1 FAIL verdict** (consciousness loop not designed -> this ADR IS the design at substrate-pattern level, with research completing detail).
- **Audit-07 §Need-Review** (Q62/Q67 deferred to ADR-066/067/068 -> formalized here at ADR-063, pre-deferral).
- **P20 substrate promotion** — P20 heartbeat + BackgroundCognition become substrate + advanced to Hermes Society level via 7 components above.

## References

- **Research + audit trail**:
  - `docs/setup-evidence/P28-P36-masterplan/research/consciousness-theory-foundations.md` §0-§9 (substrate palette + 4 theory + 6 tool + hybrid C recommendation)
  - `docs/setup-evidence/P28-P36-masterplan/research/external-consciousness-loop-research.md` (TBD — research wave in progress)
  - `docs/setup-evidence/P28-P36-masterplan/audits/round-1/audit-14-consciousness-loop-gap.md` (FAIL + 7 gaps + Round-2 fix path)
  - `docs/setup-evidence/P28-P36-masterplan/audits/round-1/audit-11-faiz-alignment.md` §2.4 (Q62/Q67/Q76/Q106/Q108)
  - `docs/setup-evidence/P28-P36-masterplan/fixes/round-1-fix-log.md` §3 F-01 + F-12
- **Canonical Q-source**: `docs/setup-evidence/P28-P36-masterplan/adr-drafts/BLDM-Hard-Locked-Faiz-Decisions.md` §4 (Consciousness) + §19 (Q39-Q53 inferred)
- **Sister ADRs**:
  - `src/life_kernel/heartbeat.py` + `cognition.py` (P20 baseline)
  - ADR-055 (society architecture; 6-loop background cognition inheritance)
  - ADR-057 (founder-only spawn; identity layer pinned at spawn)
  - ADR-059 (shared world model; dream outputs persist to S3 blackboard with provenance tag)
  - ADR-060 (wallet; budget for LLM cost of dream cycle)
  - ADR-061 (5-layer mutability + Ratchet; dream outputs subject to T1-T5 gate)
  - ADR-062 (paradigm shift; Hermes runtime autonomous)
  - ADR-064 (DAO + co-CEO + perception/decision layer owned by Guinevere)

## Footer

Version 1.0 | 2026-06-28 | Author: Guinevere + Faiz (Faiz-locked Q62/Q67/Q76/Q106/Q108/Q52/Q105) | Status: Proposed (final acceptance pending research wave completion)
