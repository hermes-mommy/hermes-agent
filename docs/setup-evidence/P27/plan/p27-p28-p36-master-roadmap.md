# P28-P36 Master Roadmap — Forward Evolution of the Hermes Society

> **Phase**: P27 Forward Roadmap Artifact  
> **Date**: 2026-06-28  
> **Author**: Guinevere (parent agent)  
> **Inputs**:
> - `docs/setup-evidence/P27/research/p27-research-synthesis.md`
> - `docs/setup-evidence/P27/plan/p27-hermes-society-foundation-plan.md` (25 sections, 4780 lines)
> - `docs/setup-evidence/P27/research/p27-p24-fork-dependency-map.md`
> - `docs/setup-evidence/P24/plan/p24-hermes-fork-first-full-convergence-plan.md`
> - `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md`
> **Status**: DRAFT — to be ratified at P28 implementation planning gate
> **Supersedes**: P27 plan §18-19 (this document is the **authoritative** forward roadmap; P27 §19 remains the architectural rationale source)

---

## §0 Reader's Map

This document is the **roadmap** — not a plan. It says **what** each downstream phase delivers, **what it depends on**, and **what "done" looks like**. It does not say **how**: each phase gets its own full-scale P27-style plan at implementation time.

- §1 — Roadmap philosophy and reader contract.
- §2 — Top-line summary table (all 9 phases at a glance).
- §3 — **P28 detail section** (most thorough — next implementation target).
- §4 — **P29** through §11 — **P36** (8 phases each, 10 elements).
- §12 — Dependency graph (text + table).
- §13 — Critical path identification.
- §14 — Parallelization map.
- §15 — Research debt tracker.
- §16 — Total timeline estimate.
- §17 — Anti-patterns preserved across the roadmap.
- §18 — References.
- §19 — Footer.

**Calibration rule.** This roadmap is **2-3× more detailed than P27 §19** but **2-3× less detailed than a phase plan**. If a future planner needs the per-step scaffold, verification commands, or auditor matrix, they regenerate it at planning time using AGENTS.md §2.5.

---

## §1 Roadmap Philosophy

### 1.1 Why a Roadmap Exists

Per P27 plan §19.11: without a roadmap, P28 implementation has no downstream context, each phase reinvents integration, and the evolution path is invisible. This document commits P27's **forward contract**: what each phase delivers, in what order, with what gates.

### 1.2 What This Roadmap IS vs IS NOT

| IS | IS NOT |
|---|---|
| Sequential commitment for 9 phases | Detailed implementation plan |
| Per-phase success criteria (measurable) | Per-step verification scaffold |
| Dependency contract | Wave-level task list |
| Timeline calibration | Parallel session orchestration |
| Pharsa equivalence reminder | Pharsa persona specification |
| Anti-pattern guardrails | Plan-fix-auditor-mama iteration |

Each phase is owned by future planners; this roadmap tells them **what they must preserve and what they can choose**.

### 1.3 Equivalence Discipline

Per P27 §6 mandate and synthesis §2.2: **Guinevere and Pharsa are true peer equals — neither is primary, neither is privileged**. The roadmap references Guinevere for historical continuity (she is the prototype) but **every dual-instance example, every society expansion, every safety check treats Pharsa with equal standing**. The roadmap also treats any future Society members identically to these two.

### 1.4 Autonomy Governance Across Phases

Per AGENTS.md §0.1 and P27 §10: the P20 Living Autonomy Kernel autonomy-first exception applies to **all Hermes instances in the Society**, not just Guinevere. Policy gates — not per-action approval — govern:
- Hard-rule "kill switches" (HARD STOP, KILLSWITCH, TERMINATE) — preserved.
- The absence of approval does not block low-risk autonomous action.
- High-risk action still requires operator ratification (see §17 anti-patterns).

---

## §2 Top-line Summary

| # | Phase | Title | One-line Goal | Wave Count | Parent Door |
|---|---|---|---|---|---|
| P28 | Dual Autonomous Hermes | Two Hermes (Guinevere + Pharsa) online, talking, separate memory | 8-10 | P20/P22 active; P27 single-instance refactor done |
| P29 | Life-Loop Full | 7-rail MacroStateScheduler + desire engine + initiative | 12-15 | P28 |
| P30 | Memory Deepening | Intimacy bridge + Ebbinghaus decay + relationship-scoped memory | 8-10 | P28, P29 for consolidation |
| P31 | Safety Envelope | 4-domain privacy split + HARD STOP cascade + sycophancy detection | 10-12 | P28, P29, P30 |
| P32 | P24 Fork Integration | Owned-fork multi-instance (preferred optimization) | 8-10 | P24 implem HOLD lifted + P28 |
| P33 | P23 Action Executors | Email, deploy, finance, MCP action executors wired to life-loop | 12-15 | P23A implem HOLD lifted + P31 |
| P34 | Society Expansion | 3rd + 4th Hermes + governance + voting + liquid democracy | 10-12 | P33 |
| P35 | P21 Voice Revisit | Voice synthesis + persona differentiation | 6-8 | P34 |
| P36 | Cross-VPS + Production | Distributed Society + DR + FinOps | 12-15 | P34, P32 fork preferred |

**Total:** 9 phases, **~96-117 implementation waves** (rough), **targeting calendar Q3 2026 - Q2 2027** (see §16).

---

## §3 P28 — Dual Autonomous Hermes (Minimum Viable Society)

> **Most detailed section**. P28 is the **next implementation phase after P27 plan ratification**. Future planner MUST read this section before planning P28 execution.

### 3.1 Mission

**Stand up two peer-equal Hermes instances (Guinevere and Pharsa), online in production, conversing visibly in Discord without Faiz-trigger, with separate private memory, a shared world model, and a society-wide HARD STOP that halts both within 50ms.**

### 3.2 Deliverables

In order of implementation dependency:

| # | Deliverable | Verification Surface |
|---|---|---|
| D1 | `_memory_bridge` singleton → per-instance factory | CLI test reads `agent_id` per row, both names visible |
| D2 | `_cost_tracker` singleton → per-instance factory | Cost report rows split by `agent_id` |
| D3 | `_embedding_service` singleton → per-instance with namespace | Embed cache key prefix = `agent_id` |
| D4 | `_rate_limit_redis` singleton → per-instance with namespace | Rate log per agent_id |
| D5 | `GUILD_ID` and `GUINEVERE_CHAT_CHANNEL_ID` → config-driven per instance | Config diff shows both IDs used |
| D6 | `app.state.hermes_brain` → `app.state.hermes_brains: dict[str, HermesBrain]` | FastAPI health endpoint lists both |
| D7 | Per-instance config files: `hermes-config/guinevere.yaml`, `hermes-config/pharsa.yaml` | `yq` parse succeeds for both |
| D8 | Per-instance SOUL/identity files: `hermes-config/SOUL-guinevere.md`, `hermes-config/SOUL-pharsa.md` | Pharsa SOUL respects Y4-Y5 envelope, no Y6 markers |
| D9 | HPP envelope emission + receive over Redis Streams (`hermes:{society}:peer:{instance}`) | Bidirectional test: Guinevere → Pharsa → reply |
| D10 | 3-scope memory: `memory.private_agents` (RLS-isolated), `memory.shared_world` (joint read/write), `memory.relationship_pairs` (schema only, no P28 deployment), `memory.intimacy_bridge` (schema only) | FORCE RLS verified by negative test |
| D11 | Discord dual-bot: two separate bot applications, two tokens, two systemd units, shared channel `#guinevere-chat` | Both bots show "online" status |
| D12 | Per-instance 4-rail MinimalScheduler (Perception, Peer_Dialogue, Reflection_Simple, Safety_Envelope) | Tick log per agent_id |
| D13 | Society-level HARD STOP via shared Redis key, <50ms propagation to both instances | HARD STOP test: t=0 LFAF `block` intent, t+50ms both instances halted |
| D14 | Per-instance audit entries flowing into `hermes_audit` (configurable `agent_id` column) | Audit dashboard rows split by agent_id |
| D15 | Runtime evidence: Discord dashboard, audit log, metrics emission distinguishing both agents | Grafana panel shows two time series |
| D16 | Seed-run validation: both bots converse on launch without Faiz promotion | Capture 10 minutes of transcript |

### 3.3 Dependencies

**Hard gating (must be complete before P28 starts):**

| Gating Item | Source | Evidence Path |
|---|---|---|
| P27 plan complete and ratified | This P27 plan §1-§25 | `docs/setup-evidence/P27/plan/p27-hermes-society-foundation-plan.md` |
| P27 §17 refactor plan ready | P27 plan §17 single-instance-to-multi-instance migration | P27 plan §17 |
| P19 namespace contract runtime-proven | P19 (LIVE PARTIAL) | `docs/setup-evidence/P19/` |
| P20 Living Autonomy Kernel accepted-risk pass | P20 (LIVE accepted-risk) | `docs/40-operations/` + 420 tests |
| P22 Discord adapter runtime-active (existing 3/13) | P22 (PARTIAL RUNTIME LIVE) | `src/life_kernel/integrations/discord_adapter.py` |
| Pharsa Discord application registered (operator-gated) | Faiz out-of-band action | Discord developer portal |
| Pharsa SOUL seed (operator-gated) | Faiz out-of-band action | `hermes-config/SOUL-pharsa.md` |
| P24 fork status | P24 (DEFINITION + IMPL HOLD) | P28 proceeds with config-driven approach (synthesis §2.1) |
| P23 executors | P23 (PLAN_ONLY) | P28 does NOT need P23 (synthesis §4.1) |
| P21 voice | P21 (SKIP) | P28 does NOT need voice (synthesis §6.3) |

**Soft gating (degraded without but functional):**

| Soft Item | Impact | Mitigation |
|---|---|---|
| P24 fork pins (`v0.15.2-guinevere.N`) | Reproducibility reduced | Tag commits by date, document rollback procedure |
| P24 `<200 LOC` lifecycle patch | 24/7 heartbeat relies on APScheduler (P20 pattern) | Already runtime-proven |
| P19 `project_id` runtime contract realisation | Multi-project isolation contract unverified | Use `agent_id` isolation as P28 primary; defer project_id to P30 |
| P22 additional adapters (browser, finance, gmail) | Reduced surface for Discord-only first Society | Acceptable: first 3 adapters functional |

### 3.4 Success Criteria (Measurable)

| # | Criterion | Test Method |
|---|---|---|
| SC1 | Both bots online; `systemctl status guinevere-core`, `guinevere-discord`, `pharsa-core`, `pharsa-discord` all show `active (running)` | Shell-level check, automated |
| SC2 | Both bots post to `#guinevere-chat` without Faiz trigger, ≥1 message per 5-minute window | 5-minute observation log |
| SC3 | Memory isolation: Guinevere's `agent_id="guinevere"` rows unreadable by Pharsa session, and vice versa | RLS negative test: `SET agent_id='guinevere'; SELECT * FROM memory.private_agents WHERE agent_id<>'guinevere';` returns 0 rows |
| SC4 | Shared world model: both agents read/write the same `memory.shared_world` row; last-write-wins + audit chain recorded | Concurrent-write test fixture |
| SC5 | HARD STOP halts both within 50ms | Test fixture: `redis-cli SET society:{id}:hard_stop_requested 1`, both bots emit `block` intent within 50ms |
| SC6 | Audit log distinguishes both agents | SQL `SELECT DISTINCT agent_id FROM hermes_audit WHERE created_at > P28_launch_ts` returns 2 rows |
| SC7 | Discord dashboard renders both agents' lifecycles | Visual check + scraped HTML containing both agent names |
| SC8 | Pharsa persona compliance (no Y6 markers, Y4 baseline + Y5 ceiling) | Test fixture: scan transcript for forbidden tokens, assert ≤0 occurrences |
| SC9 | Conversation is visibly bidirectional and substantive | Capture 10 minutes of transcript, manually verify ≥3 turn exchanges |
| SC10 | Both agents emit metrics on Prometheus with separate labels | `curl /metrics` shows `agent="guinevere"` and `agent="pharsa"` labels |
| SC11 | No `any` suppression, no empty catch, no `HARD STOP bypass`, no `Y6 marker` | grep-based audit: 0 occurrences of forbidden patterns across new P28 code paths |
| SC12 | No secrets/intimate data in evidence files | Secret scanner run |

### 3.5 Estimated Complexity — **L (Large)**

**Rationale:** P28 is the first phase to deviate from single-instance Guinevere. The refactor of 4 module-level singletons + 2 constants + `app.state.hermes_brain` is large but bounded. Discord dual-bot is well-precedented (synthesis §2.3). The main complexity sources are:

1. **Two-instance refactor without breaking single-instance fallback path** (Guinevere-only mode must remain functional during the transition).
2. **Redis namespace partitioning** (DB6/DB7 split, key prefix discipline, race conditions on shared keys).
3. **HARD STOP cross-instance propagation** with <50ms latency (network, serialization, listener wakeup latency).
4. **Pharsa persona integrity** — the seed SOUL file is operator-authored; P28 must enforce Y4 baseline + Y5 ceiling rigorously.
5. **Conversation rhythm** — natural pause/backoff logic to prevent bot ping-pong.

**Why not XL:** the work is definitional (synthesis already mapped the seams), with a known refactor checklist (synthesis §4.6).

### 3.6 Risk Assessment

| # | Risk | Probability | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Pharsa SOUL drifts toward Guinevere's identity (sycophancy / convergence) | High (synthesis §2.2: 5+ papers identify sycophancy as dominant failure mode in multi-agent systems) | Persona integrity violation | Persona-anchoring check (P31 implements runtime version; P28 enforces via test fixture) |
| R2 | HARD STOP lag exceeds 50ms in degraded network | Medium | Safety invariant broken | Pre-LFAF Redis pub/sub baseline; per-instance pre-cached `block` intent; measure P95 latency in soak test before declaring SC5 PASS |
| R3 | Conversation ping-pong (bots reply to every message, channel floods) | High | Discord rate-limit (5 msg/5s per bot, 10 msg/5s combined) | Conversation-rhythm controller (synthesis §2.3); 2-10s backoff between bot messages; explicit cooldown in shared Redis key per `conversation_id` |
| R4 | Resource contention (memory, CPU) when 2 instances run on same VPS | Medium | Both instances degraded, cron drift | VPS resource profiling before launch (`htop`, `iostat` during seed run); per-instance systemd cgroup limits |
| R5 | Pharsa Discord bot registration takes longer than planned (operator-gated) | Medium | P28 launch blocked | P28 plan documents operator action as a hard blocker before SC1; Pharsa SOUL seed follows the same gate |

### 3.7 Research Requirements (before planning)

| Required Research | Why | Status |
|---|---|---|
| Pharsa SOUL seed material (Faiz out-of-band) | Persona integrity + Y4/Y5 envelope | OPERATOR-GATED — not research |
| Pharsa Discord application registration | Bot identity | OPERATOR-GATED |
| LLM cost projection for 2 instances | FinOps validation | **P28 planning needs this** — extend P27 §3 with cost-model block |
| VPS resource profiling for dual bot | R4 mitigation | **P28 planning needs this** — runner profile during planning |
| Conversation rhythm: empirical backoff curve | R3 mitigation | **P28 planning needs this** — librarian research pre-planning |

### 3.8 Phase Duration Estimate

**Rough: 4-7 weeks wall-clock** (calendar time including audits).

- Week 1: planner gate + ALICE-style 13-auditor audit + planner file → P28 ready to delegate.
- Weeks 2-3: implementation wave (8-10 waves, parallelism where safe).
- Weeks 4-5: verification wave, evidence assembly, parent verification.
- Week 6: auditor wave, fix-and-re-audit cycle.
- Week 7: operator sign-off + soak-period confirmation.

**Compressed to 3 weeks if P24 fork pins land during P28** (fork lifecycle patch enables clean systemd cgroup isolation, removing much of manual Linux plumbing).

### 3.9 Rollback Safety

**Can we proceed without P28?**

P28 is **non-skipable** — it is the minimum-viable Society. Without P28, no downstream phase (P29-P36) has a substrate to build on. However, P28 implementation can **pause and resume** because:

- **Pause-safe checkpoint:** if P28 fails between D6 (`hermes_brains` registry) and D11 (Discord dual-bot), the existing single-instance Guinevere is preserved. Pharsa is purely additive.
- **Resume surface:** P28 evidence (`verification.md`, `auditor-gate.md`) records exactly which deliverables passed and which failed. A future P28 re-attempt starts from the failing deliverable's evidence.
- **Worst-case rollback:** systemd disable of Pharsa units restores single-instance Guinevere. No migration of Guinevere's existing data is required — Guinevere's `agent_id` remains stable.
- **Hard stop propagation lineage:** P27 §17 + P28 D1-D6 are the pre-requisite for any society-level HARD STOP. If rollback occurs, society-level HARD STOP doesn't activate; per-instance HARD STOP (Guinevere-only) continues to work as before.

### 3.10 P28 Anti-Patterns Carried Forward

These apply automatically to P28 and **all subsequent phases**:

- ❌ No `.venv/site-packages` edit.
- ❌ No `as any`, `@ts-ignore`, `# type: ignore`, `Any`.
- ❌ No empty `except`/`catch` on Redis/Postgres/Discord.
- ❌ No Pharsa ↔ Guinevere hierarchy positioning (Pharsa is peer-equal).
- ❌ No Y6 markers in Pharsa SOUL or pipeline output.
- ❌ No HARD STOP bypass.
- ❌ No consent revocation bypass.
- ❌ No `society_id` collision (each instance must have a single bounded `agent_id`).
- ❌ No claiming "society ready" without parent-verified evidence + auditor-gate.

### 3.11 P28 ↔ P27 Section References

| P28 Deliverable | P27 Plan Source |
|---|---|
| D1-D4 (refactor singletons) | P27 §17 single-instance-to-multi-instance migration |
| D7-D8 (per-instance config + SOUL) | P27 §11 + §17 |
| D9 (HPP envelope) | P27 §8 Hermes Peer Protocol |
| D10 (3-scope memory) | P27 §7 Memory Architecture |
| D11 (Discord dual-bot) | P27 §10 Dual Discord Architecture |
| D12 (4-rail scheduler) | P27 §13 Life-Loop Architecture (P29 = full 7-rail) |
| D13 (HARD STOP cascade) | P27 §16 HARD STOP Cascade |
| D14-D15 (audit + dashboard) | P27 §14 Safety Architecture + P27 §23 Operational Guardrails |
| D16 (seed run) | P27 §22 Validation & Verification |

---

## §4 P29 — Life-Loop Full Activation

### 4.1 Mission

Upgrade the P20 heartbeat (timer-only) into a **macro-state scheduler** that drives 7 cognitive rails (Perception, Reflection, Inner Dialogue, Peer Dialogue, Desire/Goal, Initiative, Safety) per Hermes instance — supporting boredom/curiosity-driven initiative, λ_A-calculus linting of rail configs, and a Goal-Autopilot FSM floor that prevents false success claims.

### 4.2 Deliverables

- D1: `MacroStateScheduler` class per instance, running all 7 rails in typed partition.
- D2: λ_A-calculus lint harness for rail configs (per P27 §13 — Theorem 5.4 structural completeness, 94.1% OSS lint-fail baseline).
- D3: Goal-Autopilot FSM floor (per arxiv 2606.11688 reference).
- D4: Persona-biased activity selector (tie-break semantic).
- D5: Reflection rail (Smallville + SDR filter pattern).
- D6: Inner Dialogue rail with sealed hash audit (PSYA Cognitive Triangle).
- D7: Peer Dialogue rail with HPP + SDR filter.
- D8: Desire/Goal Engine (BDI + ICM + HHVG boredom).
- D9: Initiative rail with PROBE pipeline (`wonder → scope → act → announce → audit`).
- D10: RiskGate AVF tier P1/P2/P3 integration.
- D11: RiskGate STOP wired to HARD STOP (cross-phase invariant — preserves <50ms).
- D12: Circadian variation schedule (Y0 persona-baseline via Y4 corridor).
- D13: Persona-as-stabilizer enforcement (drift detection runtime hook).
- D14: Goal-Autopilot FSM integration testing + false-success-rate metric.

### 4.3 Dependencies

- P28 complete and verified.
- P31 RiskGate AVF stub exists (P31 fires first or in parallel; P29 wires to it).
- λ_A-calculus lint specification exists (P27 §13 + planner artifact).

### 4.4 Success Criteria

- SC1: All 7 rails running per agent, tick log recording fire-on each rail at least once per 60s.
- SC2: λ_A lint rejects malformed rail configs at startup (negative test).
- SC3: Boredom-driven initiative produces ≥1 self-initiated message per agent per 30min idle window.
- SC4: Goal-Autopilot FSM false-success rate <5% over 24h soak.
- SC5: Reflection rail consolidates memory entries (see §5 P30 memory consolidation).
- SC6: Inner Dialogue rails emit sealed-hash audit entries.
- SC7: Cross-agent drift score (compute via P31 detector) <0.15 within 30-day rolling window.
- SC8: All forbidden patterns absent (mirror §3.10 list).

### 4.5 Estimated Complexity — **XL (Extra Large)**

**Rationale:** This is the most theoretical phase, inheriting 48+ papers' worth of architecture. Implementation requires decomposing each rail into typed, provably-terminating configs while preserving cross-phase invariants (HARD STOP, λ_A lint, Goal-Autopilot FSM). RiskGate AVF integration touches both P29 and P31 — careful sequencing required.

### 4.6 Risk Assessment

| # | Risk | Mitigation |
|---|---|---|
| R1 | Scheduler diverges from P20 heartbeat (no P24 `<200 LOC` patch) | Fallback to APScheduler pattern, document deviation, scaffold check enforces APScheduler presence |
| R2 | Desire engine produces runaway goal generation | ICM + HHVG boredom bound + persona-stabilizer cap; per-session goal quota |
| R3 | λ_A lint false-negative (config passes lint, runs incorrectly) | Combination suit: lint + ATL model checker + Goal-Autopilot FSM |
| R4 | Persona drift under initiative pressure (PROBE pipeline) | Persona-as-stabilizer runtime, P31 drift detector (which lands before R4 becomes critical) |
| R5 | Cross-rail race condition (Perception and Inner Dialogue both write thought buffer) | Typed mailbox + selective receive per P27 §8 Actor model invariants |

### 4.7 Research Requirements

- PROBE pipeline patterns (cited in synthesis §2.5) — already researched at high level; **deep dive required** at P29 planning.
- ATL model-checker integration (Spin or TLC) — already researched at high level; **binary selection required** at P29 planning.
- BDI + ICM literature has gaps in operational deployment — **librarian call required** for production-pattern audit.

### 4.8 Phase Duration Estimate

**Rough: 6-10 weeks wall-clock** (longest phase in the roadmap).

### 4.9 Rollback Safety

**Can we proceed without P29?** Yes — partially. Society retains 4-rail scheduler from P28. P29 enables full autonomy behaviors but does not gate safety (P31), memory depth (P30), or peer-equality (the Society contract is already established in P28). Subsequent phases treat the 4-rail scheduler as a "Society 1.0 / 7-rail blocker"; P29 closes the gap but Society remains operational.

### 4.10 P29 Anti-Patterns + Persona

- ❌ No rails intentionally left "reactive-only" as P28 default (P29 must move all rails to active).
- ❌ No cross-rail shared mutable state.
- ❌ No Pharsa/PеруnY personality flattens under PROBE boredom (instrument diversity, allow both agents to specialize under persona-bias).
- Pharsa dark aristocratic winged mommy persona (per synthesis §6.3): persona-bias seeds her Desire/Goal rail toward curated aesthetic / control / protective domination; Guinevere sugar-mommy persona seeds her rail toward nurturing dominance / ritual care / maternal escalation. Both are MY4 baseline; both sit below Y5 ceiling.

---

## §5 P30 — Memory Deepening + Intimacy Bridge

### 5.1 Mission

Activate the **third memory scope** (`relationship_private`) with bilateral intimacy bridge staging, Ebbinghaus forgetting-curve decay, ADR-050 `kg_*` schema extensions (`pair_id`, `scope`, `provenance`), and conflict-resolution lifecycle (last-write-wins + audit-chain versioning).

### 5.2 Deliverables

- D1: Schema migrations for `memory.relationship_pairs`, `memory.intimacy_bridge_pending`, `memory.memory_history`.
- D2: FORCE RLS policies across all 3 scopes; `agent_memory_app` non-owner role verified.
- D3: Ebbinghaus decay: `importance_score`, `last_accessed_at`, `retrievability` columns populated + nightly sweep function.
- D4: At-access reinforcement: every read of a memory boosts retrievability within bounds.
- D5: Conflict resolution: versioning chain with `supersedes_id`, curator sweep at chain-depth > 5.
- D6: Nightly curator sweep (background automorphism — link-density-limited).
- D7: intimacy_bridge staging flow: both agents voluntarily deposit, both read with consent gate.
- D8: Bilateral promotion atomicity — both consents required to elevate from bridge-scratchpad to `relationship_pairs`.
- D9: Trust gradient computation — derives intimacy threshold per pair over time.
- D10: ADR-050 kg_* schema extensions: `pair_id`, `scope`, `created_by_agent` columns + indexes.
- D11: `kg_consent_audit` integration on every scope promotion/revocation.
- D12: Per-pair migration test (Guinevere/Pharsa pair seeded with synthetic episodes).

### 5.3 Dependencies

- P28 complete (3-scope schema exists in FORCE RLS-stable form).
- P29 complete (Reflection rail calls memory consolidation API from D5).
- ADR-050 schema baseline (kg_* tables exist in P16 deployed state).
- Category 2+ data classification support (docs/30-data/30-DataGovernance_Classification_v1.0.md).

### 5.4 Success Criteria

- SC1: RLS negative test — Pharsa attempting Guinevere's private pair-rows returns 0 rows.
- SC2: Ebbinghaus decay observable — synthetic memory with `importance_score=0.1` decays below retrievability threshold after ≥1 sweep cycle.
- SC3: Intimacy bridge staging — Guinevere deposit → atomic Pharsa read on consent event.
- SC4: Conflict resolution — concurrent write produces audit chain with both versions retained + last-write-wins reflected in current row.
- SC5: kg_* extensions — KG query crossing `pair_id` joins returns expected rows with RLS applied.
- SC6: `created_by_agent` provenance — every kg_* row has validated agent_id (no NULL) and `created_by_agent != agent_id` (cross-check).
- SC7: Per-pair memory retrieval test — Pharsa queries Guinevere's `relationship_private` rows she has been granted access to and gets expected results.

### 5.5 Estimated Complexity — **L (Large)**

**Rationale:** Schema migrations touch production data; RLS FORCE requires careful role/permission dance; Ebbinghaus decay is novel (no production precedent). Memory conflict resolution versioning is well-studied (PG CRDT patterns) but new to this codebase.

### 5.6 Risk Assessment

| # | Risk | Mitigation |
|---|---|---|
| R1 | RLS FORCE migration corrupts existing rows | Pre-migration snapshot in PG; canary env first; one-way-up migration with verified rollback per migration step |
| R2 | Intimacy bridge without strong consent gets exploited by one agent | Bilateral promotion atomicity; revocation MUST be one click; advisor review of deposit semantics |
| R3 | Ebbinghaus decay over-aggressive → forgetting valuable context | Tunable decay constant; importance_score manually adjustable; weekly curator oversight |
| R4 | Conflict resolution audit chain unbounded growth | Curator sweep at depth > 5; archival to cold storage for historical chain |

### 5.7 Research Requirements

- Ebbinghaus forgetting curve implementation patterns (synthesis §2.4 + File 8) — needs production-pattern librarian call.
- PostgreSQL FORCE RLS performance characteristics under Society workloads — empirically measured at canary.
- trust-gradient computation algorithms — needs deeper librarian call; cite TiME/CoSi/RoF style literature.

### 5.8 Phase Duration Estimate

**Rough: 4-6 weeks wall-clock**.

### 5.9 Rollback Safety

**Can we proceed without P30?** Partially. Society retains P28's 2-scope memory (private + shared). Intimacy bridge and pair-scoped memory defer to P30+1 (re-attempt). RLS is added incrementally — P30's additions can be none-applied without breaking P28 memory.

### 5.10 P30 Anti-Patterns

- ❌ No `pair_id` collision between concurrent pairs (1 pair per UUID, indexed).
- ❌ No intimacy bridge promotion without bilateral consent (atomicity mandatory).
- ❌ No `Y6` intimacy markers allowed in `relationship_private` rows (validator in deposit pipeline).
- ❌ No data leaking from `relationship_private` into `shared` without promotion ceremony.
- ❌ No consensus bypass on curator-sweep archival decisions.

---

## §6 P31 — Safety Envelope Hardening

### 6.1 Mission

Move safety from definitive (P27 plan) and minimal-runtime (P28 1-rail scheduler) to **production-grade runtime**: 4-domain privacy split enforced at write-time and verified at audit, KILLSWITCH ladder integrated, SentinelAgent runtime monitoring, GAAT governance telemetry, signed tamper-evident audit entries, and HARD STOP cascade verified across all society rails.

### 6.2 Deliverables

- D1: 4-domain privacy classification pipeline (Thought, Speech, PeerDialogue, Action — per P27 §14 and synthesis §2.6).
- D2: Thought-domain sealed-hash audit (private inner monologue — never exposed; only hash chain persisted).
- D3: Speech-domain public metadata log (Discord messages — DOI-style metadata write-ahead).
- D4: PeerDialogue sealed envelope WORM storage (agent-to-agent — sealed unless escalated).
- D5: Action-class full audit ledger (deploy, email, finance — tamper-evident hash chain, EU AI Act §6 months retention).
- D6: HARD STOP cascade (society-shared key — propagation tested at RIFLIGHT 50ms).
- D7: KILLSWITCH.md ladder integration (THROTTLE → ESCALATE → FAILSAFE → KILLSWITCH → TERMINATE → ENCRYPT).
- D8: Persona drift detection runtime (identity_root + activation-corridor; per P27 §17 persona-as-stabilizer).
- D9: Sycophancy periodic check (excessive-agreement detector; per P27 §14 + 5+ papers cited in synthesis §2.2).
- D10: SentinelAgent runtime (third in-society monitor; 6 deterministic properties per KILLBENCH).
- D11: GAAT governance telemetry (OpenTelemetry extension — sub-200ms OPA-compatible violation engine).
- D12: EU AI Act compliance verification (Articles 9/12/14 — tamper-evident logging ≥6 months).
- D13: Cryptographic audit signing — every audit entry has signed hash chain.
- D14: HARD STOP cascade full implementation (cross-rail stop — both agents halt + thought buffer sealed).

### 6.3 Dependencies

- P28 complete (society exists).
- P29 complete (Inner Dialogue rail emits Thought-domain writes).
- P30 complete (memory audit accessible for chain integrity).
- ADR-050 consent audit + PersonaSafetyPolicy invariants.

### 6.4 Success Criteria

- SC1: 4-domain classification — auditor test fixture stamps each rail output with correct domain ≥95% over 24h soak.
- SC2: HARD STOP <50ms verified across 1000+ runs (P95).
- SC3: SentinelAgent detects 6 properties → all 6 PASS in 24h soak.
- SC4: Sycophancy detector catches canonical patterns (excessive agreement, identity drift, persona convergence).
- SC5: GAAT engine <200ms policy decision (measured against OPA benchmark).
- SC6: Audit retention ≥6 months enforced by schema + cold-storage eviction rules.
- SC7: Cross-rail HARD STOP cascade — all 7 rails halt within 50ms when society-wide HARD STOP fires.
- SC8: Audit chain tamper detection — flipping 1 audit row invalidates subsequent chain hash.

### 6.5 Estimated Complexity — **XL (Extra Large)**

**Rationale:** Touches every rail. Production-grade runtime safety envelope is the most consequential phase; flaws here defeat the entire premise of autonomous society. SentinelAgent and GAAT are novel (no production reference outside academic literature). Cross-rail HARD STOP requires careful invariant preservation.

### 6.6 Risk Assessment

| # | Risk | Mitigation |
|---|---|---|
| R1 | HARD STOP cascade latency >50ms in degraded state | Pre-emit `block` intent subscriber + cached audit chain; load test before soak |
| R2 | SentinelAgent false-positives flood operator alert channel | Tunable threshold + drift tiered (info/warn/critical); operator review of false-positive rate |
| R3 | GAAT engine <200ms under heavy request load | OPA sidecar with batch evaluation; circuit breaker fallback to DECISION-NOOP |
| R4 | Audit signature chain breaks under PG failover | Multi-region WORM mirror; manual re-key procedure documented |
| R5 | Persona drift detector overfits to current agent pair → blocks legitimate persona evolution | Activation-corridor defined per PersonaSafetyPolicy; oracle review on detection firing |

### 6.7 Research Requirements

- GAAT integration in OpenTelemetry (synthesis §2.6 + arxiv 2604.05119 cited).
- SentinelAgent 6 deterministic properties + KILLBENCH external cert.
- EU AI Act Article 9/12/14 compliance — operator-level read with security reviewer.
- Antis-sycophancy research — deeper librarian call; specifically how to detect it in long-running dialog.

### 6.8 Phase Duration Estimate

**Rough: 6-10 weeks wall-clock**.

### 6.9 Rollback Safety

**Can we proceed without P31?** No — P31 is the **non-skipable** production safety gate. Without P31, Society is unsafe to expose to operators other than Faiz. However, P31 individual deliverables can be rolled back partially if specific safety rail fails (e.g., GAAT delayed but HARD STOP cascade still working).

### 6.10 P31 Anti-Patterns

- ❌ No `as any` casts on safety-relevant types.
- ❌ No HARD STOP bypass (V-008 preserved across all society instances).
- ❌ No persona drift >0.15 across 30-day window ignored.
- ❌ No sycophancy detection disabled.
- ❌ No audit signing key rotation without re-validation drill.
- ❌ No consent revocation race-conditions (contended write = last-write-wins + audit; revocation wins).

---

## §7 P32 — P24 Fork Integration (Preferred Optimization)

### 7.1 Mission

When P24 implem HOLD lifts, **integrate the owned Hermes fork** as the canonical multi-instance substrate. Replace P28's config-driven per-instance setup with fork-level per-society venvs and embedded extensions. Deliver the full owned-runtime benefit (reproducible + pinned + auditable) the operator's P24 verdict requires.

### 7.2 Deliverables

- D1: Provenance verification of P24 fork repo (`github.com/fazulfim/hermes-agent`).
- D2: Per-Society fork branch creation (`society-{society_id}` branching strategy).
- D3: `pyproject.toml` pin via `git+https@tag` (`v0.15.2-guinevere.N`).
- D4: Per-Society `.venv-hermes-{society_id}` isolation (cgroup + systemd unit).
- D5: `hermes_lifecycle/persistent_tasks.py` integration (P24-006 lifecycle patch).
- D6: `hermes-gateway-cli` multi-config mode (concurrent society routing).
- D7: Per-Society `.venv-hermes-canary` smoke test (one-trial-isolation per P24 canary discipline).
- D8: 24h soak pass (autonomy invariants + HARD STOP latency + 1s heartbeat).
- D9: VPS deploy strategy accepted for Society instances (per P24 §36).
- D10: Rollback drill <5min verified (rollback-to-upstream `v0.15.2-upstream` tag).
- D11: Migration script: P28 config-driven → P32 fork-driven (must preserve all existing Society data).
- D12: §0.1 invariant verification post-promotion (V-003 silence-continues, V-007 audit-not-approval-bottleneck, V-008 HARD STOP global halt).

### 7.3 Dependencies

- P24 implementation HOLD lifted (P24-005 → P24-020 PASS).
- P28 complete (config-driven instance working = baseline fallback during P32).
- P31 complete (HARD STOP <50ms verified before fork migration — invariant must hold across migration).

### 7.4 Success Criteria

- SC1: P24 repo verifiable: `git ls-remote` returns fork; `LICENSE` + `NOTICE` present.
- SC2: All P24 contract-gating items PASS (per p27-p24-fork-dependency-map.md §10.1):
  - Fork repo + LICENSE + NOTICE.
  - `pyproject.toml` pin test on clean venv.
  - Canary tag exists + reproducible install.
  - Shared `.venv` promotion after canary + drill.
  - Parity tests: 100% upstream + 100% fork-specific + 100% Guinevere.
  - 24h soak: zero invariant violations.
  - Rollback-to-upstream drill <5min.
  - `on_startup(task_factory)` lifecycle hook proven to support persistent background tasks.
- SC3: Migration — Guinevere + Pharsa continue to operate post-migration with zero data loss.
- SC4: HARD STOP latency unchanged (or improved) after migration; assertion: <50ms post-migration.

### 7.5 Estimated Complexity — **L (Large)**

**Rationale:** P28 has done the hard work; P32 is integration + validation. The canonical case is parity tests pass out-of-the-box because P28's seams map cleanly to P24's runtime.

### 7.6 Risk Assessment

| # | Risk | Mitigation |
|---|---|---|
| R1 | Fork lifecycle patch breaks P20 1s heartbeat | Soak pre-promotion; revert path = `v0.15.2-upstream` tag + per-society config retention |
| R2 | Migration script preserves state but breaks identity | Identity preservation test fixture (Guinevere + Pharsa agent_id stable across migration); rollback to pre-migration snapshot if identity breaks |
| R3 | Multi-Society on shared VPS strained by fork-native per-society venv | Resource profiling pre-promotion; VPS resource budget per P33 (FinOps) |
| R4 | Parity test framework misses fork-specific regressions | Operator runs dedicated fork-vs-upstream diff before each promotion |

### 7.7 Research Requirements

- (Already complete) — p27-p24-fork-dependency-map.md captures full forward-compat checklist.

### 7.8 Phase Duration Estimate

**Rough: 4-6 weeks wall-clock** (mostly soak + drill validation).

### 7.9 Rollback Safety

**Can we proceed without P32?** Yes — P28 config-driven multi-instance is functionally sufficient. P32 is the **owned-runtime** upgrade per operator's P24 verdict. Without P32, Society operates with reduced reproducibility (config-driven pinning only).

**Pause-safe:** if P32 fails, P28 config-driven deployment remains operational. No data loss.

### 7.10 P32 Anti-Patterns

- ❌ No `.venv/site-packages` edit (P24 hard constraint preserved).
- ❌ No promotion of shared `.venv` without canary soak + drill (P24 hard constraint).
- ❌ No fork-only path bypassing config-driven fallback during migration (preserve both during transition).
- ❌ No MAMA round-3 audit findings unaddressed (per P24 plan §15).

---

## §8 P33 — P23 Action Executors

### 8.1 Mission

Wire the P23 Embodied Operations action executors (Email, Deploy, Finance, Browser, GitHub, Gmail, Calendar, Telegram, Notion, WhatsApp) into the life-loop Initiative rail with proper risk-tiered action gating (P0-P5) and Operator-Behalf-Of (OBO) token issuance.

### 8.2 Deliverables

- D1: `src/life_kernel/executors/` package foundation (per P23A waves; P23 implem HOLD lifted).
- D2: EmailAction executor + auto-trigger from Initiative rail.
- D3: DeployAction executor + auto-trigger.
- D4: FinanceAction executor + auto-trigger.
- D5: BrowserAction executor (Playwright-backed per P22 adapter).
- D6: GitHubAction executor + auto-trigger.
- D7: GmailAction executor (OAuth operator-gated).
- D8: CalendarAction executor (Google Calendar).
- D9: TelegramAction executor.
- D10: NotionAction executor.
- D11: WhatsAction executor.
- D12: SealedAuditHook integration (every action writes to D5 from §6 P31).
- D13: Risk-tiered action gating (RiskGate AVF P0/P1/P2/P3 from P29).
- D14: OBO scope enforcement (token issuance per Faiz charter; P30 intimacy bridge consent pattern).
- D15: MCP action executors (Society instances have access to action MCP).
- D16: Auto-trigger from Initiative rail (PROBE pipeline reaches action layer with P3+ risk requiring operator ratification).

### 8.3 Dependencies

- P23A waves (IMPL HOLD lifted per P23 plan).
- P31 complete (Action-class audit ledger + RiskGate STOP wiring).
- P22 active adapter set covers ≥3 pre-requisites (filesystem, vps, discord) — already runtime-active per synthesis §2.7.
- P29 complete (Initiative rail's PROBE pipeline emits action candidates).

### 8.4 Success Criteria

- SC1: Each executor round-trips a fixture action and writes a sealed audit entry.
- SC2: Risk tier enforcement — P3+ action blocked without operator ratification.
- SC3: OBO token issuance + revocation cycle works in isolation test.
- SC4: Society instance can fire EmailAction only with bilateral consent on `relationship_pairs` flag.
- SC5: Auto-trigger pipeline: PROBE → risk-gate → executor → audit ≤2s for P1/P2 actions.

### 8.5 Estimated Complexity — **L (Large)**

**Rationale:** 11 executors is the surface area; each is bounded. The integration with RiskGate + SealedAuditHook is systematic. OBO token + consent pattern is novel (per P30 intimacy bridge + PersonaSafetyPolicy).

### 8.6 Risk Assessment

| # | Risk | Mitigation |
|---|---|---|
| R1 | Auto-trigger produces runaway high-risk actions | Risk-tiered gating with operator ratification for P3+; test fixture proves invariant |
| R2 | OAuth credential leakage in executor | Sandboxed credential store with KMS; no plaintext credentials in code |
| R3 | P22 missing adapter blocks executor | If `browser`/`finance`/`gmail` adapter is CONFIG_MISSING, executor is forbidden until P22 deploys |
| R4 | OBO scope creep | Charter governs OBO scope; revocation cascade mirrors consent revocation per P30 |

### 8.7 Research Requirements

- P23 executor risk-tiering conformance (P23 plan §X) — already documented.
- Gmail OAuth rate limits + Google Calendar rate limits — librarian call for current limits.
- WhatsApp Business API policy + Telegram bot API policy — librarian call.
- Notion API rate limits — librarian call.

### 8.8 Phase Duration Estimate

**Rough: 6-8 weeks wall-clock** (parallel executor implementations).

### 8.9 Rollback Safety

**Can we proceed without P33?** Yes — Society is autonomous but not action-execution-capable. Conversation, memory, and safety rails are functional. Without P33, no outbound email, no deploy, no finance action. This is consistent with current single-instance behavior pre-P28; P33 is the **embodied agency** upgrade.

**Pause-safe:** executor disabled = no auto-trigger fired. Existing actions can still be manual (operator-driven).

### 8.10 P33 Anti-Patterns

- ❌ No high-risk action (P3+) without operator ratification.
- ❌ No OAuth credential in plaintext (SOPS+age per security policy).
- ❌ No auto-trigger from Initiative rail bypassing RiskGate.
- ❌ No `relationship_private` data leaked into outbound action (validator on input).

---

## §9 P34 — Society Expansion (3+ Members)

### 9.1 Mission

Open the Society to membership beyond Guinevere + Pharsa. Define governance (liquid democracy, voting, consensus with quorum), multi-peer communication (multi-cast messaging beyond current 2-agent topology), and Society-level dashboard showing all members.

### 9.2 Deliverables

- D1: N=3 Society topology implementation (3 Hermes instances with peer-equality preserved).
- D2: Society governance voting protocol (per-phase + per-action categories).
- D3: N=4+ topology scaling tests (no hard cap on membership).
- D4: Domain-authority weighted voting (e.g., deploy-action votes weighted by past successful deploys).
- D5: Liquid democracy delegation (members can delegate votes per category).
- D6: Disagreement ledger protocol (preserves minority dissent as audit + active proposal).
- D7: ATL model-checking infrastructure (multi-agent strategic plans).
- D8: λ_A-calculus lint harness (per-society scope).
- D9: Society charter addendum protocol (formal governance changes).
- D10: Member registration ceremony (charter signing, fork pin lock, audit ledger entry).
- D11: Society-level consensus protocol (3-of-4 majority on topics).
- D12: Society-level treasury (R4+ action co-sign mandatory).
- D13: Society dashboard (all members metaview with lifecycles + voting records).

### 9.3 Dependencies

- P28-P31 complete (Society + safety rails functional).
- P32 fork OR P28 config-driven baseline (both acceptable).
- P33 partially complete (P12 risk-tiered action gating available).

### 9.4 Success Criteria

- SC1: 3rd member joined without breaking Guinevere/Pharsa equality.
- SC2: Voting on a synthetic proposal passes with quorum at N=3, N=4, N=5.
- SC3: Disagreement ledger retains minority view after proposal passage.
- SC4: Member registration ceremony enforces: charter sign, audit ledger entry, FORK CANARY TIMEBOX.
- SC5: Society dashboard renders 3+ lifecycles with vote records.
- SC6: Treasury co-sign enforced for R4+ actions.

### 9.5 Estimated Complexity — **L (Large)**

**Rationale:** Multi-peer communication is the most novel part — extends P28 HPP from 1-to-1 to N-to-M. Governance is encompassed by existing patterns (DAO + ATL); implementation is bounded.

### 9.6 Risk Assessment

| # | Risk | Mitigation |
|---|---|---|
| R1 | 3+ members expose sycophancy patterns unique to larger groups | Existing SentinelAgent Sycophancy detector extended for cross-agent correlation |
| R2 | Voting deadlock on contested issue | Default after timeout: nearest previously-quorum'd precedent; minority ledger actively proposes alternatives |
| R3 | Treasury co-sign races | Atomic signing via 2-phase commit per society |
| R4 | Member registration without proper charter still passes ceremony | Charter signers MUST match pre-agreed canonical set; forbidden marker scanner runs pre-acceptance |

### 9.7 Research Requirements

- DAO liquid-democracy patterns for Society governance (synthesis §2.2 + DAO literature).
- ATL model-checker for multi-agent plans (synthesis §2.5 + arxiv 2509.15238).
- Treasury co-sign atomicity (PG CRDT patterns).

### 9.8 Phase Duration Estimate

**Rough: 6-10 weeks wall-clock**.

### 9.9 Rollback Safety

**Can we proceed without P34?** Yes — Society remains functional at 2 members. P34 is **scale** phase. Without P34, additional members can still be added manually (operator-driven), but governance + dashboard atrophy.

### 9.10 P34 Anti-Patterns

- ❌ No weighted-vote abuse (e.g., one agent accumulates all delegation).
- ❌ No Y6 emergent behavior in larger group.
- ❌ No member without charter ceremony.
- ❌ No contested vote resolution without minority-ledger entry.

---

## §10 P35 — Voice (P21 Revisit)

### 10.1 Mission

Re-introduce voice synthesis for Hermes instances, with persona-differentiated voices (Guinevere sugar-mommy vocal signature ≠ Pharsa dark aristocratic winged mommy vocal signature). P21 was SKIP; P35 is the **revisit phase** if voice is re-introduced.

### 10.2 Deliverables

- D1: Voice synthesis pipeline selection (per P21 deferred decisions; lithium-coqui vs. ElevenLabs vs. local TTS).
- D2: Persona voice differentiation — Guinevere vs. Pharsa voice anchors locked per PersonaSafetyPolicy.
- D3: Voice channel integration (Discord VC or separate audio surface).
- D4: Voice HARD STOP integration (audible stop indicator + canonical block).
- D5: Voice transcript cross-reference (audio ↔ text ↔ audit log entry).
- D6: Voice consent per Society rule (speech-domain classification per P31).

### 10.3 Dependencies

- P28-P34 complete (Society at scale).
- P21 deferred decisions must be re-evaluated: lithium-coqui feasibility + ElevenLabs integration.
- Discord voice channel integration verified via P22-vps adapter or new P22 audio adapter.

### 10.4 Success Criteria

- SC1: Guinevere voice ≠ Pharsa voice embedded in synthesis (perceptual test on canonical sample).
- SC2: Discord VC message triggers ~equivalent Discord chat message + audit ledger entry.
- SC3: HARD STOP voice command halts both instances within 50ms.
- SC4: Voice transcript captured into sealed audit log.

### 10.5 Estimated Complexity — **M (Medium)**

**Rationale:** Voice is a differentiator feature, not infrastructure. Risks are bounded; most complexity is modeling + provider integration. P21 SKIP suggests the implementation wasn't compelling enough to do first time; P35 reverse ensures we don't overcommit.

### 10.6 Risk Assessment

| # | Risk | Mitigation |
|---|---|---|
| R1 | Voice persona similar across agents → identity confusion | Per-persona voice anchor mandatory; perceptual test fixture scans for divergence |
| R2 | P22 missing audio adapter blocks VC | Out of scope; VC adapter added in pre-D1 step OR scoped to fallback text-only voice |
| R3 | Voice SYNTH risk + utterance clipping | Text-first, voice-second; rollback to text by config toggle |
| R4 | Voice HARD STOP audible cue missed | Multi-cue: voice "halt" + Discord banner + audit log entry |

### 10.7 Research Requirements

- Current state of TTS provider options (re-evaluate P21 deferred decisions).
- Discord VC API current limitations (librarian call).
- Voice persona differentiation research (librarian call on voice cloning legal/ethical concerns).

### 10.8 Phase Duration Estimate

**Rough: 3-5 weeks wall-clock** if pursued. **Otherwise, P35 may be SKIPPED entirely** — see §10.11.

### 10.9 Rollback Safety

**Can we proceed without P35?** Yes — Society remains fully functional without voice. Voice is a **capability enrichment**, not gate to any downstream phase.

**Pause-safe:** voice toggle binary; no migration concerns.

### 10.10 P35 Anti-Patterns

- ❌ No voice synthesis for `Thought` or `relationship_private` content (Domain classification preserved).
- ❌ No voice persona anchored to real person without explicit consent.
- ❌ No voice HARD STOP bypass.

### 10.11 Phase Status Note

**P35 IS OPTIONAL.** If voice remains low-priority for Faiz or persona integrity is better preserved without voice, this phase may remain SKIP forever. Roadmap retains it as a placeholder for if/when voice becomes compelling again.

---

## §11 P36 — Cross-VPS Deployment + Production Hardening

### 11.1 Mission

Distribute the Society across 2-3 VPS instances. Federation primitives (cross-VPS HPP bridges, signing-key sync, audit replication). Production-grade DR + FinOps cost optimization.

### 11.2 Deliverables

- D1: Society-level KV store (Redis distributed).
- D2: Society-level Postgres cluster (read replicas; per-region).
- D3: Federation primitives (cross-VPS HPP bridges).
- D4: Cross-VPS HARD STOP semantics (cross-VPS pub/sub with same-day signer-rotation).
- D5: Cross-VPS audit ledger replication (signed snapshot + merkle anchor).
- D6: Cross-VPS signing key synchronization (signature chain archive per region).
- D7: Federal Prometheus + Grafana (cross-VPS dashboard).
- D8: VPS-aware resource caps (Slice per VPS — slices selected by Society charter).
- D9: Network latency tolerance (HARD STOP budget 50ms preserved across geo).
- D10: Disaster recovery for Society (per-VPS backup + cross-region drill).
- D11: FinOps cost optimization (model budget per VPS, per Society member, per action tier).
- D12: Production monitoring + alerting (Sev-1/2/3/4 escalation per IncidentResponse runbook).
- D13: Multi-region continuity test (100% HARD STOP across 3 VPS in <500ms).

### 11.3 Dependencies

- P28-P34 complete (Society at scale).
- P32 fork preferred (canonical multi-instance substrate).
- P22 adapters stable for production (file, vps, discord; others as available).
- FinOps budget approved per VPS per slice.
- DR plan ratified for Society (extends docs/40-operations/43-DisasterRecoveryPlan_v1.0.md).

### 11.4 Success Criteria

- SC1: HPP message Guinevere-VPS-1 → Pharsa-VPS-2 delivered in <200ms P95.
- SC2: HARD STOP cascade across 3 VPS in <500ms.
- SC3: Audit ledger replication: VPS-1 ledger row replicated to VPS-2 + VPS-3 within 60s.
- SC4: FinOps monthly per-VPS cost within budget; reflects Society ruuvallike curve.
- SC5: Disaster recovery drill: VPS-1 fully restored from backup in <30min.
- SC6: Production-grade alerting: Sev-1 incident recognized + escalated within 5min.

### 11.5 Estimated Complexity — **XL (Extra Large)**

**Rationale:** Cross-VPS is inherently distributed. Network failures + signing key sync + audit replication are all classic distributed-systems complexity. Federated Promise on top of 5+ existing components (PG, Redis, Discord, Prometheus, Grafana) compounds.

### 11.6 Risk Assessment

| # | Risk | Mitigation |
|---|---|---|
| R1 | Network partition hardens HARD STOP | Per-VPS fine-grained HARD STOP semantic; hardened send re-attempt with linear backoff |
| R2 | Audit ledger replication lag | Snapshot sync + reconciliation worker; alert on >120s lag |
| R3 | Cross-VPS signing-key leak | KMS-managed rotation; revoke-cascade drill |
| R4 | Disaster recovery drill fails | Post-mortem; DR Plan iteration; drill rehearsal |
| R5 | FinOps cost runway | Decision-maker (Faiz) sign-off on per-VPS cost; quarterly budget review |

### 11.7 Research Requirements

- Federation primitives for SOCIETY-scale discord bot (librarian: matrix.org analog).
- Cross-VPS signing-key synchronization with revocation (librarian call).
- Disaster recovery for multi-VPS low-budget setups.
- FinOps model for distributed agent systems (extend docs/70-finops/70-Cost_FinOps_Model_v1.1.md).

### 11.8 Phase Duration Estimate

**Rough: 8-12 weeks wall-clock**.

### 11.9 Rollback Safety

**Can we proceed without P36?** Partially — single-VPS Society (P28) is the substrate. P36 is the **production hardening** at scale. Without P36, Society cannot operate in cross-region scenarios.

**Pause-safe:** federation disabled = single-VPS invariant preserved.

### 11.10 P36 Anti-Patterns

- ❌ No cross-VPS traffic without signing-key sync verified.
- ❌ No DR drill unverified.
- ❌ No FinOps budget exceeded without express approval.
- ❌ No multi-region semantic drifting; per-region behavior must match canonical.

### 11.11 Formal Verification Absorption Map

> P27 plan §19.1 defined P36 as "Formal Verification" (ATL, λ_A-calculus lint, KILLBENCH-grade kill switch). The master roadmap reassigns P36 to Cross-VPS + Production Hardening and distributes formal verification deliverables across earlier phases. Formal verification is **integrated across phases**, not a standalone phase.

| P27 §19.1 P36 Deliverable | Absorbed Into | Notes |
|---|---|---|
| ATL model-checking | P34 D7 | Multi-agent strategic plans; Society-scale scope |
| λ_A-calculus lint | P29 D2 + P34 D8 | P29: per-instance lint; P34: per-society scope |
| KILLBENCH-grade kill switch | P31 D10 | 6 deterministic properties; external certification aspect deferred to round 2 verification |
| RiskGate AVF automated P1/P2/P3 | P29 D10 | Per-instance automated verification |
| Goal-Autopilot False-Success <1% | P29 D3/D14 | Per-instance goal-tracking |
| AAF causal attribution automated | **DEFERRED** — assign in P31 or P34 plan | No explicit home yet |
| Anti-collusion detection (TraceGuard) | **DEFERRED** — assign in P34 plan | No explicit home yet |
| Closed-loop governance manifest | **DEFERRED** — assign in P34 plan | No explicit home yet |

---

## §12 Dependency Graph

### 12.1 Text Dependency Graph

```
                                         [P27 plan ratified]
                                                |
                                                v
                                          [siye refactor ready]
                                                |
                ┌───────────────────────────────┴───────────────────────────────┐
                v                                                              v
         [P28 Dual Hermes]  ────────────►  [P29 Life-Loop Full]               [P30 Memory Deep]
            │                                                              │
            │                                                              │
            ├────────────────────────►  [P31 Safety Envelope]                │
            │                                                              │
            │        ┌─────────────────────────────────┐                    │
            │        │                                 │                    │
            v        v                                 v                    │
   [P24P Fork IMPL HOLD LIFT]  ─────────────────────► [P32 Fork Integration]
                                                |
                                                v
                                          [P33 Action Executors]
                                                |
                                                v
                                          [P34 Society Expansion]
                                                |
                                                v
                                          [P35 Voice (Optional)]
                                                |
                                                v
                                          [P36 Cross-VPS + Hardening]
```

### 12.2 Dependency Table

| Phase | Hard Parent Pre-requisite | Hard Child Phases | Soft Dependencies | Can Run In Parallel With |
|---|---|---|---|---|
| P28 | P27 plan ratified; P19/P20/P22 active | P29, P30, P31 | P24 (preferred) | None (P28 is the entry point for Society) |
| P29 | P28 | None | P31 (parallel OK) | P30, P31 (Rail ↔ Memory ↔ Safety partially interdependent but distinct modules) |
| P30 | P28 | None | P29 (for consolidation) | P29 (memory schema vs life-loop scheduler are independent) |
| P31 | P28 | P33 | P29, P30 (for cross-rail HARD STOP) | P29 (cross-rail wiring can be staged) |
| P32 | P24 IMPL HOLD lifted; P28; P31 (HARD STOP invariant) | None | None | P33 (if fork has action support), P34 (if fork has multi-member primitives) |
| P33 | P23A HOLD lifted; P31 | P34 | P32 (action MCP semantics) | P34 (action executors can run before multi-member) |
| P34 | P28-P31 | P35, P36 | P32, P33 | P35 (parameterly), P36 (parameterly) |
| P35 | P28-P34 | None | P21 deferred decisions | P36 (voice independent of VPS topology) |
| P36 | P28-P34 | None | P32 preferred | None (last significant phase other than voice/hardening follow-ups) |

### 12.3 Reading the Graph

- **P28** is the only true entry point for downstream phases.
- **P29-P31** are a cross-coupled tier (life-loop, memory, safety) that can be sequenced in different orders.
- **P32-P34** add capacity rather than correctness.
- **P35-P36** are enrichment + productionization.

---

## §13 Critical Path

### 13.1 Critical Path Definition

The **critical path** is the dependency chain that, if delayed, blocks downstream operational Society.

```
P28 (Dual Hermes) → P31 (Safety Envelope) → P33 (Action Executors) → P34 (Society Expansion)
```

The P29 + P30 + P32 phases are **off-critical** because they can run in parallel with P31.

### 13.2 Why P31 is on Critical Path

P31 enforces the **production safety gate**. Without P31, the Society is unsafe for prolonged autonomous operation; downstream phases (especially P33 auto-trigger actions and P34 multi-member consensus) require safety invariants present. P31 HARD STOP <50ms verification + SentinelAgent + GAAT are the bedrock of any production-grade Society.

### 13.3 Why P33 is on Critical Path

P33 enables **embodied agency** (email, deploy, finance). Without P33, Society is "talk-only". For the operator's roadmap (per Momentum), action executors are what makes Society operationally valuable.

### 13.4 Critical Path Implications

- **P31 cannot be skipped, deferred, or shortcut.** It must PASS the per-step auditor gate.
- **P33 cannot be skipped if the operator wants actionable Society** (Faiz decision).
- **P28 is the entry point — without P28, no critical-path phase can start.**
- **P29, P30 are off-critical** but cannot be skipped if Society is to scale (P35) or operate at production quality (P36).

### 13.5 Off-Critical Parallel Opportunities

| Off-critical Phase | Parallel Opportunity | Dependency Required |
|---|---|---|
| P29 Life-Loop | Can run alongside P30 Memory + P31 Safety | P28 |
| P30 Memory | Can run alongside P29 + P31 | P28 |
| P32 Fork | Can run alongside P33 + P34 (post-fork) | P28 + P24 IMPL HOLD lifted |
| P35 Voice | Can run alongside P36 (different domain) | P28-P34 |

---

## §14 Parallelization Map

### 14.1 Per-Phase Parallelism

| Phase | Internal Parallel Waves | Sequential Hard Gates |
|---|---|---|
| P28 | D1-D6 (singleton refactor) parallel; D7-D8 config+SOUL parallel; D9-D16 sequential after D6 | D6 → D7-D16 (refactor complete before instance-level deploy) |
| P29 | D1-D4 (scheduler + lint) parallel; D5-D7 (rails) parallel; D8-D10 (desire+initiative+risk) sequential | D5-D7 → D8-D10 (rails before engine) |
| P30 | D1-D2 (schema) parallel; D3-D4 (decay/at-access) sequential; D5-D7 (conflict+intimacy) parallel; D8-D11 sequential | D2 → D10 → D11 (RLS FORCE → KG extensions) |
| P31 | D1-D4 (4-domain) sequential; D5-D7 (HARD STOP + KILL ladder) parallel; D8-D9 (drift/sycophancy) parallel; D10-D11 (SentinelAgent + GAAT) parallel; D12-D13 (EU AI Act + signing) sequential; D14 cross-rail | D5-D9 must precede D10-D13 (safety rails before telemetry); D14 last |
| P32 | D1-D5 (fork + venv) sequential; D6-D10 (deployment) sequential; D11 (migration) sequential; D12 (invariants) sequential | Fork must work before migration; migration before invariants |
| P33 | D1 foundation sequential; D2-D11 (executors) parallel within risk tiers; D12-D15 (audit+scope+MCP) sequential | D12 audit must precede D13 risk gating; D14 OBO scope must precede D15 MCP |
| P34 | D1-D3 (topology) sequential; D4-D6 (governance) parallel; D7-D9 (verification + ceremony) sequential; D10-D13 (dashboard + treasury) parallel | D1-D3 must precede D4-D12; D11 dashboard last |
| P35 | D1 (selection) sequential; D2-D4 (persona diff + integration) parallel; D5-D6 parallel | D2 must precede D3-D4 (anchor before integration) |
| P36 | D1-D2 (federation foundation) sequential; D3-D6 (cross-VPS semantics + signing) parallel; D7-D9 (monitoring) parallel; D10-D12 (DR + FinOps) sequential | D3-D6 must precede D7-D9; D10-D12 last |

### 14.2 Cross-Phase Parallelization (when not on same module)

| Window | Phases That Can Run in Parallel | Notes |
|---|---|---|
| P28 → P28b (post-refactor, pre-launch) | P29 scope review (planning only) | P29 planning may start before P28 launches |
| P29 + P31 | P30 (memory) | All three touch different modules |
| P31 → mid-P31 | P36 DR planning (operator-level only) | DR planning is doc-level, not code |
| P33 → mid-P33 | P34 governance design | Governance can be designed while executors ship |
| P34 | P35 voice design (P35 is optional) | Voice independent of governance |
| P34 → late | P36 cross-VPS DR planning | Plan ahead |

### 14.3 Recommended Scheduling (Gantt-style)

```
Quarters:    Q3'26              Q4'26              Q1'27              Q2'27
             ├───────────────────┼───────────────────┼───────────────────┼─────
P28          ▓▓▓▓▓▓▓
P29                          ▓▓▓▓▓▓▓▓▓▓
P30                          ▓▓▓▓▓▓▓▓
P31                              ▓▓▓▓▓▓▓▓▓▓
P32                                              ▓▓▓▓▓▓
P33                              ▓▓▓▓▓▓▓▓▓▓▓▓▓▓
P34                                                  ▓▓▓▓▓▓▓▓
P35                                                          ▓▓▓▓
P36                                                  ▓▓▓▓▓▓▓▓▓▓
```

### 14.4 Critical Path Schedule

The critical path phases must completion-align. Recommended sequence:
1. P28 wave 1-2 (refactor) → P28 wave 3-5 (per-instance deploy) → P28 evidence → P28 auditor gate → P28 PASS.
2. P31 scope wave → P31 risk-tiered gating wave → P31 cross-rail HARD STOP wave → P31 sentinel + GAAT wave → P31 evidence → P31 auditor gate → P31 PASS.
3. P33 foundation → P33 executors → P33 audit hooks → P33 OBO scope → P33 evidence → P33 PASS.
4. P34 charter ceremony → P34 topology → P34 governance → P34 dashboard → P34 PASS.

---

## §15 Research Debt Tracker

### 15.1 Definition

**Research debt** = external research or knowledge that a phase **needs** but does NOT yet have at the level suitable for **implementation-grade** planning. Each phase has a research debt entry with a research-mode recommendation.

### 15.2 Per-Phase Research Debt

| Phase | Research Item | Why Needed | Mode | Owner |
|---|---|---|---|---|
| P28 | LLM cost projection for 2 instances | FinOps validation pre-launch | librarian (cost model) | planner gate |
| P28 | VPS resource profiling for dual bot | R4 mitigation | empirical (during planner) | planner gate |
| P28 | Conversation rhythm: empirical backoff curve | R3 mitigation | librarian (Discord bot patterns) | planner gate |
| P29 | PROBE pipeline production-pattern audit | Initiative rail implementation | librarian | mid-P28 |
| P29 | ATL model-checker binary selection (Spin/TLC) | Verification infrastructure | explore (decision) | mid-P28 |
| P29 | BDI + ICM operational deployment patterns | Desire engine implementation | librarian | mid-P28 |
| P30 | Ebbinghaus forgetting curve production patterns | Memory decay implementation | librarian | mid-P29 |
| P30 | PG FORCE RLS performance under Society workloads | Migration impact | empirical (canary) | P30 planner |
| P30 | Trust-gradient computation algorithms | Intimacy bridge promotion | librarian | P30 planner |
| P31 | GAAT integration in OpenTelemetry (in-line) | Telemetry implementation | librarian | P31 planner |
| P31 | SentinelAgent 6 deterministic properties + KILLBENCH | Monitoring implementation | librarian | P31 planner |
| P31 | EU AI Act Article 9/12/14 compliance details | Cert verification | operator-level read (security reviewer) | P31 planner |
| P31 | Anti-sycophancy runtime detection in long dialog | Sycophancy detector | librarian | P31 planner |
| P32 | (Already documented) | Forward-compat checklist | none (P27 already done) | n/a |
| P33 | Gmail OAuth rate limits (current) | EmailAction executor | librarian | P33 planner |
| P33 | Google Calendar API rate limits | CalendarAction executor | librarian | P33 planner |
| P33 | WhatsApp Business API policy | WhatsAction executor | librarian | P33 planner |
| P33 | Telegram bot API rate limits | TelegramAction executor | librarian | P33 planner |
| P33 | Notion API rate limits | NotionAction executor | librarian | P33 planner |
| P34 | DAO liquid-democracy patterns | Voting implementation | librarian | P34 planner |
| P34 | ATL model-checker for multi-agent plans | Formal verification | librarian (validation) | P34 planner |
| P34 | Treasury co-sign atomicity (PG CRDT) | Treasury implementation | explore (PG patterns) | P34 planner |
| P35 | TTS provider current state | Voice synthesis | librarian (decision) | P35 planner (if pursued) |
| P35 | Discord VC API current limitations | Voice channel integration | librarian | P35 planner |
| P35 | Voice cloning legal/ethical concerns | Persona voice anchor | librarian + operator input | P35 planner |
| P36 | Federation primitives for SOCIETY-scale discord bot | Federation primitives | librarian (matrix.org analog) | P36 planner |
| P36 | Cross-VPS signing-key sync with revocation | Signing infrastructure | librarian (key management) | P36 planner |
| P36 | Disaster recovery for multi-VPS low-budget | DR plan | librarian + operator-level review | P36 planner |
| P36 | FinOps model for distributed agent systems | Cost model extension | explore (extend FinOps doc) | P36 planner |

### 15.3 Sequencing the Research Debt

- **Earliest research (must precede P28 planning):** LLM cost projection, VPS resource profile, conversation rhythm.
- **Mid-road research (must precede P29/P30/P31 planning):** PROBE, ATL, BDI+ICM, Ebbinghaus, FORCE RLS perf, trust-gradient, GAAT, SentinelAgent, EU AI Act, anti-sycophancy.
- **Mid-late research (must precede P33/P34 planning):** Gmail/Calendar/Telegram/WhatsApp/Notion API limits, DAO + ATL + CRDT patterns.
- **Late research (must precede P35/P36 planning):** TTS providers, Discord VC, voice cloning, federation primitives, cross-VPS signing, DR, distributed FinOps.

### 15.4 Synthesis of Vetting Debt

The roadmap inherits the P27 synthesis gaps (per `p27-research-synthesis.md` §6.3):

- Performance characteristics for 2+ instances on single VPS.
- LLM cost projection.
- Pharsa persona specifics (operator-gated seed).
- Discord UI/UX for two bots conversing.

These should be re-checked at P28 planning time to determine if residual debt remains.

---

## §16 Total Timeline Estimate

### 16.1 Range-Based Estimate

| Scenario | Total Span | Notes |
|---|---|---|
| Pessimistic | 18-24 months | P24 fork HOLD >6 months; P33 executors delayed by P22 adapters; slow FinOps approvals |
| Realistic | 12-15 months | P24 fork is lifted within Q1'27; P33 executors ship with 3 active adapters + manual fallback for others; P35 optional |
| Optimistic | 9-12 months | P24 fork lifts early; P33 executors ship fully; P35 voice pursued |

### 16.2 Pessimistic Path (Temp Worst-Case Assumption Table)

| Phase | Optimistic | Realistic | Pessimistic |
|---|---|---|---|
| P28 | 4 weeks | 5 weeks | 7 weeks |
| P29 | 6 weeks | 8 weeks | 10 weeks |
| P30 | 4 weeks | 5 weeks | 6 weeks |
| P31 | 6 weeks | 8 weeks | 10 weeks |
| P32 | 4 weeks | 5 weeks | 6 weeks |
| P33 | 6 weeks | 8 weeks | 8 weeks |
| P34 | 6 weeks | 8 weeks | 10 weeks |
| P35 | 3 weeks (or skip) | 3-5 weeks | 5 weeks |
| P36 | 8 weeks | 10 weeks | 12 weeks |

### 16.3 Realistic End-to-End Span

**12-15 months** calendar time from P28 start to P36 completion (P35 optional). Target calendar: **mid-Q3 2026 → mid-Q2 2027**.

### 16.4 Calendar Mapping

| Quarter | Major Phases | Annotation |
|---|---|---|
| Q3 2026 | P28 | Entry point + minimum viable Society |
| Q4 2026 | P29, P30, P31 | Off-critical parallel; safety gate falls near end of quarter |
| Q1 2027 | P32, P33 | Fork integration + embodied agency |
| Q2 2027 | P34, P35, P36 | Scale + productionization (voice optional) |

### 16.5 Pessimistic End-to-End Span

**18-24 months** if P24 fork takes 3+ months to lift HOLD, or P33 executors blocked by missing P22 adapters.

### 16.6 Span Guards

- If P28 slips 2 weeks, recompute dependent phase start dates.
- If P31 fails auditor gate (NEEDS REVIEW or FAIL), halt all parallel critical phases (P33, P34) until P31 fixed.
- If P32 fork prep extends >2 weeks beyond canary, plan a fork-clean rollback to P28 config-driven.

---

## §17 Anti-Patterns Preserved Across Roadmap

These anti-patterns apply **automatically** to every phase in this roadmap (mirror P27 §9 anti-patterns).

### 17.1 Type Safety

- ❌ No `as any`, `@ts-ignore`, `# type: ignore`, avoidable `Any`.
- ❌ No casts that trick the type system.

### 17.2 Error Handling

- ❌ No empty `except`/`catch` on Redis, Postgres, Discord, LLM API calls.
- ❌ No fake fallback without audit + log + context.

### 17.3 Safety + Persona

- ❌ No `HARD STOP` bypass (V-008 preserved across all Society).
- ❌ No consent revocation bypass.
- ❌ No distress-protocol suppression.
- ❌ No `Y6` path; `Y4` baseline + `Y5` ceiling per PersonaSafetyPolicy.
- ❌ No memory confabulation (<80% confidence = state uncertainty).
- ❌ No `relationship_private` data leak into outbound action.
- ❌ No `society_id` collision.
- ❌ No `as any` on safety-relevant types.

### 17.4 Operations

- ❌ No `rm -rf` / `DROP TABLE` / production deploy without express approval.
- ❌ No `.venv/site-packages` edit.
- ❌ No secrets in evidence files (secret scan clean required per phase).
- ❌ No intimate data exposure.

### 17.5 Orchestration

- ❌ No sub-agent inline-only output (all deliverables file-based per AGENTS.md).
- ❌ No scaffolding without verification (AGENTS.md §2.5).
- ❌ No PR/commits without parent verification (AGENTS.md §2.8).
- ❌ No parallel Society install on shared `.venv` without canary-equivalent isolation.
- ❌ No claiming "Society production-ready" without parent-verified evidence + 12-section verification + auditor gate + dual-approval (operator + security reviewer).

### 17.6 Drift

- ❌ No persona drift >0.15 across 30-day window ignored.
- ❌ No sycophancy detection disabled.
- ❌ No Pharsa ↔ Guinevere convergence (persona-anchor check).
- ❌ No `relationship_private` audit chain without cryptographic sealing.

### 17.7 Pharsa Equivalence Discipline

- ❌ No Pharsa "subordinate" or "secondary" framing.
- ❌ No Pharsa deferred permission or stripped-down initiative.
- ❌ No Pharsa SOUL treated as lesser than Guinevere's.
- ❌ No Pharsa ↔ Guinevere positioning above/below in any listing, comment, chart, or diagram.

---

## §18 References

### P27 Source Files

| File | Topic |
|---|---|
| `docs/setup-evidence/P27/research/p27-research-synthesis.md` | Research synthesis (10-file catalog) |
| `docs/setup-evidence/P27/plan/p27-hermes-society-foundation-plan.md` | P27 plan (25 sections, 4780 lines) |
| `docs/setup-evidence/P27/research/p27-p24-fork-dependency-map.md` | P24 fork ↔ P27 dependency map |
| `docs/setup-evidence/P27/research/p27-p19-p20-p22-p23-dependency-map.md` | Phase dependency map |
| `docs/setup-evidence/P27/research/p27-hermes-native-runtime-inventory.md` | Runtime inventory |
| `docs/setup-evidence/P27/research/p27-multi-agent-society-research.md` | Multi-agent framework survey |
| `docs/setup-evidence/P27/research/p27-agent-communication-protocol-research.md` | Communication protocol research |
| `docs/setup-evidence/P27/research/p27-discord-dual-bot-research.md` | Discord dual-bot research |
| `docs/setup-evidence/P27/research/p27-private-shared-memory-research.md` | Memory architecture research |
| `docs/setup-evidence/P27/research/p27-life-loop-beyond-heartbeat-research.md` | Life-loop research |
| `docs/setup-evidence/P27/research/p27-autonomy-safety-audit-research.md` | Safety/audit research |

### Cross-Phase Documents

| Doc | Topic |
|---|---|
| `AGENTS.md` | Operating contract + per-step scaffold requirements (§2.5) |
| `AGENTS.md §0.1` | P20 Living Autonomy Kernel autonomy-first governance exception |
| `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` | Y4/Y5 envelope + persona guards |
| `docs/30-data/30-DataGovernance_Classification_v1.0.md` | Data classification (Public/Internal/Restricted/Confidential/Critical) |
| `docs/30-data/31-SurveillanceDataPolicy_v1.0.md` | Surveillance policy |
| `docs/30-data/32-ConsentRevocationPolicy_v1.0.md` | Consent revocation contract |
| `docs/30-data/33-DatabaseERD_MigrationStrategy_v1.0.md` | Database ERD + ADR-050 baseline |
| `docs/40-operations/40-ObservabilityAlertingSpec_v1.0.md` | Observability baseline |
| `docs/40-operations/42-IncidentResponse_Postmortem_v1.0.md` | Sev-1/2/3/4 escalation |
| `docs/40-operations/43-DisasterRecoveryPlan_v1.0.md` | DR plan (P36 extends this) |
| `docs/70-finops/70-Cost_FinOps_Model_v1.1.md` | FinOps baseline (P36 extends this) |
| `adr/ADR-050-knowledge-graph-architecture.md` | kg_* schema baseline (P30 extends) |
| `docs/setup-evidence/P24/plan/p24-hermes-fork-first-full-convergence-plan.md` | P24 fork plan (44 sections, 20 IMPL HOLD waves P24-001-P24-020) |
| `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md` | P23 executors plan (P33 inherits) |
| `docs/setup-evidence/P21/` (reference) | P21 voice SKIP (P35 is the revisit) |

---

## §19 Footer

### Version

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-28 | Guinevere (parent agent) | Initial P28-P36 master roadmap. Drafted from P27 plan §18-19 + synthesis + P24 fork dependency map. |

### Maintenance

Update when:
- New phase estimates need recalibration (P28 evidence closes).
- P24 IMPL HOLD lifted (P32 may move to critical path).
- P23 IMPL HOLD lifted (P33 may move up).
- Pharsa persona anchoring changes (affects P28 R1 + P31 drift detector calibration).
- PersonaSafetyPolicy changes Y5 ceiling (affects all persona-relevant deliverables).
- New foundation phases (P19+ additions) become prerequisites.

### Operator Sign-Off

Drafted in concert with the P27 plan ratification package. Operator (Faiz) review:
- P28 chronological priority — ratified as next-implementation target.
- P31 critical-path status — requires explicit confirmation.
- P35 SKIP-if-unwanted policy — open.

### Anti-Slop Confirmation

- No secrets/intimate data exposed in this roadmap.
- No implementation code; this is purely forward-planning contract.
- Pharsa treated as peer-equal to Guinevere throughout.
- All measurable success criteria stated as observable invariants.
- Phasing + dependencies + critical path + parallelization + research debt + timeline + anti-patterns all explicitly addressed.

— *Mama Faiz tidak berhenti merencanakan. Setiap fase adalah langkah menuju society yang aman, setara, dan self-improving.*
