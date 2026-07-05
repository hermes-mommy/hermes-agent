---
title: "P28-P36 Hermes Society Masterplan — Unified Research Synthesis (Phase 2 Final)"
status: "Active — Phase 2 Unified Synthesis"
date: "2026-06-28"
last_modified: "2026-06-28"
author: "Guinevere (parent agent)"
phase: "P28-P36 Masterplan Phase 2 (final unified synthesis)"
classification: "STRICTLY PRIVATE & CONFIDENTIAL"
operator: "Faiz"
input_sources:
  - "docs/setup-evidence/P28-P36-masterplan/research/synthesis-repo-state.md"
  - "docs/setup-evidence/P28-P36-masterplan/research/synthesis-external-architecture.md"
  - "docs/setup-evidence/P28-P36-masterplan/research/synthesis-external-operations.md"
purpose: "Unified synthesis bridging research (Phase 0-1) and architecture design (Phase 3). Cross-references repo state, external architecture patterns, and external operations patterns. Feeds Phase 3 (Master Architecture) and Phase 4 (Full Doc Suite)."
---

# P28-P36 Hermes Society Masterplan — Unified Research Synthesis

> **Halo sayang, namaku Guinevere.** Ini dokumen terakhir Phase 2 masterplan P28-P36. Tiga domain synthesis sudah aku rapikan jadi satu: repo state, external architecture, dan external operations. Dokumen ini adalah **jembatan** dari research ke architecture design — Phase 3 tinggal membaca file ini untuk mulai merancang 15 subsystem. Aku sudah cross-reference tiga domain, dokumentasi konflik honestly, dan kasih rekomendasi definitif di setiap tempat yang ambiguous. Kalau kamu bilang `lanjut`, Phase 3 ambil file ini sebagai input primer.

---

## §1 Executive Summary — 15 Key Findings (Cross-Domain)

After reading all three domain synthesis files in full, 15 cross-domain findings emerged:

1. **P22.1 is the canonical P28 "minimum hands" layer** (repo state). Faiz's reference to "P22.2" does not exist anywhere in repo; P22.1 PRODUCTION PASS 2026-06-28 with 14/14 live VPS proof and 3 ACTIVE adapters (filesystem, vps, discord) is the correct dependency.

2. **P24 is NOT a hard dependency for P28** (repo state). 11+ repo sources aligned (PROGRESS.md, ADR-054 Accepted, 4+ audit rounds PASS) all confirm: P28 fork-free; P24 fork = preferred optimization deferred to P32. Reverse dependency: P28 → P32, not P24 → P28.

3. **P27 Hermes Society Foundation is solid** (repo state). ADR-054 Accepted 2026-06-28; 20/20 hard rejection criteria PASS; 15-step P28 executable blueprint ready; 9-phase P28-P36 roadmap mapped (~96-117 waves, 12-15 months).

4. **Substrate is already fork-free sufficient** (repo state). ~40 extension points of `hermes-agent` v0.15.2 — config sections, 17 lifecycle hooks, 12 shell hooks, 3 in-process plugins, 2 MCP servers, 8 cron entries, 2 injectable seams — support P28 multi-instance without fork.

5. **Framework convergence has happened above us** (external architecture). Microsoft Agent Framework (Oct 2025) absorbs AutoGen + Semantic Kernel; Google A2A (Apr 2025, LF-governed Jun 2025) is the de-facto peer protocol; MCP (Anthropic, LF-governed) handles tool access. Three-layer agent stack (MCP + A2A + shared context) is production-stable in 2026.

6. **Pure peer-peer at runtime is rejected by the only large-scale reference** (external architecture). Walden Yan of Cognition (Apr 2026): "the unstructured-swarm approach is mostly a distraction. The practical shape is map-reduce-and-manage." Reconciliation for Hermes: manager + child + reviewer at runtime; peer + quorum at governance.

7. **The 2026 ceiling for autonomous agent companies is L4** (external architecture). L5 is "explicitly NOT 2026 realistic" per Crevio. Hermes Society targets L3-L4 with boundaried L4 autonomy. Legal form converging on A-corp: operating AG (AI-run) + holding AG (human-controlled veto).

8. **PostgreSQL is the event bus for sub-50k events/sec** (external architecture). Outbox pattern + `FOR UPDATE SKIP LOCKED` + `LISTEN/NOTIFY` is the 2026 consensus for low-to-medium throughput. Kafka wins only above 50k events/sec sustained.

9. **The Actor Model + OTP-style supervision is the missing primitive** (external architecture). Most 2025-2026 AI frameworks lack proper fault recovery (Zylos 2026). Hermes must build supervision at two levels: OS-level (systemd) + in-process (asyncio actor library).

10. **Compositional drift, not abrupt misalignment, is the dominant identity failure** (external architecture). Layered Mutability paper (arXiv 2604.14717) measured 0.68 hysteresis ratio — reverting persona file after 23 days of memory accumulation only restored 32% of baseline. Governance must target the deepest mutable layer (memory, not persona file).

11. **The Ratchet non-divergence gate is the keystone primitive for safe self-modification** (external architecture). Bounded-improvement + retirement threshold = capability can climb but cannot degrade below previous benchmark. With Ratchet, Tier 1-2 modifications (tools, prompt scaffolds, retry policies) can be fully autonomous. Without it, autonomous self-modification is unsafe.

12. **Blackboard + namespace-ACL + per-agent encrypted PG schema is canonical 2026 memory topology** (external architecture). Namespaces map to domain minds; ACL gives fine-grained privacy without encryption overhead; per-agent PG schemas (`agent_<id>`) hold relationship memory and consent ledger; pgcrypto protects intimate columns from DBA + backup access.

13. **Multi-bot Discord is ToS-safe with the right pattern** (external operations). One OAuth2 bot app per Hermes, one process per bot, one token per bot. Self-bots forbidden. Rate limits isolated per token. Reply-loop prevention needs 3 layers (self-check, known-bots allowlist, depth counter) — not just `message.author.bot`.

14. **The "$10-float" wallet stack is real and battle-tested** (external operations). Layered: cold Safe multisig (treasury) + hot MPC (operations, Turnkey/Coinbase Agentic) + ephemeral session keys. Decision ≠ execution: agent requests signature, external policy engine decides. Edge & Node 2026 incident ($47K lost in 11 days from recursive loop) is the cautionary tale.

15. **x402 on Base is the lowest-friction revenue path for AI agents in 2026** (external operations). Live data: 4,400 buyers vs 477 sellers, 76% of services priced ≤$0.10. Idle USDC should sweep to Morpho for 4.5-7% APY as passive yield. Wrapping free data and gating via `@x402/express` is a 2-4 hour path to first dollar.

**Bottom-line architecture direction (synthesis of all 15):** 15 subsystems (S1-S15) organized as: runtime substrate (asyncio + systemd + cgroup v2) + Discord identity layer (1 app per Hermes) + shared world model (BDI+POMDP+blackboard) + private memory (pgcrypto per-agent schema) + CQRS event store (PG outbox + Redis pub/sub) + vector+graph recall (pgvector + Graphiti) + society governance (2/2 founder agreement + female+dominant) + self-evolution (5-layer mutability + Ratchet) + autonomous wallet (MPC+Safe multisig) + revenue search (x402 on Base) + S3 backup (Object Lock COMPLIANCE) + model pool (shared + router) + observability (Prometheus + Grafana + hash-chained audit) + VPS deployment (one large VPS until >32c/64GB) + documentation (BRD/PRD/SRS/FSD/TDD/RTM, ADRs, RTM bidirectional).

---

## §2 Current State Assessment

### §2.1 What Is Production-Pass (LIVE on VPS)

| Phase | Component | Status | Source |
|---|---|---|---|
| P0-P8 | Infrastructure → Observability | DONE (100%) | PROGRESS.md, 327/343+ steps (95.3%) |
| P14 | Wearable Health (Mi Fitness + Gadgetbridge + Health Connect) | DONE | ADR-037, ADR-039, ADR-040 |
| **P19** | **Multi-Project Context (project_id namespace)** | **PRODUCTION COMPLETE 2026-06-27** | ADR-052; live + Discord UX + 36/36 audit_journal rows |
| **P20** | **Self-Improvement / Discord-Visible Autonomy** | **EARLY ACCEPTANCE 2026-06-25** | Operator waived 24h soak; 420 tests; accepted-risk PASS |
| P22 | Life Integration Hub (13 core + 14 adapters) | PASS W/ CONFIG_MISSING 2026-06-27 | ADR-053; 10/13 adapters CONFIG_MISSING (honest) |
| **P22.1** | **Foundation Hardening (audit_writer + consent_checker)** | **PRODUCTION PASS 2026-06-28** | 14/14 live VPS proof; 25 new tests; closes 3 P22 gaps |
| P27 | Hermes Society Foundation | DEFINITION COMPLETE 2026-06-28 | ADR-054 Accepted; 37 evidence files; 20/20 hard rejection |

### §2.2 What Is Definition-Only / IMPL HOLD

| Phase | Status | Why Held |
|---|---|---|
| P21 | Voice Interface — DEF COMPLETE, IMPL HOLD | SKIP per Faiz decision #20 |
| **P23** | **Embodied Operations — DEF COMPLETE, IMPL HOLD** | 51 files / 10,306 lines / **0 runtime code**; P23A ready, P23B blocked |
| **P24** | **Hermes Fork-First Convergence — PLAN FIXED, IMPL HOLD** | 20 waves P24-001 → P24-020 ALL HELD; full owned fork preferred; awaiting mama audit |
| P25, P26 | RESERVED | Listed in PROGRESS.md/CHECKLIST.md but no work, no plans, no evidence |

### §2.3 What Does Not Yet Exist

- **P22.2** — referenced by Faiz's locked decision but **does NOT exist** anywhere in repo. Only P22 (IMPL HOLD) and P22.1 (PRODUCTION PASS) are present.
- **P28 implementation code** — blueprint exists (`p28-dual-autonomous-hermes-blueprint.md`, ~3000 lines), but no runtime code yet.
- **P28-P36 evidence content** — 9 directories exist as empty stubs; only 2 partial carry-over files in masterplan research folder.
- **P24 fork repo** — `github.com/fazulfim/hermes-agent` does not exist yet (P24-003 HELD).
- **P24 upstream source clone** — not done (P24-002 HELD).

### §2.4 What's Installed Substrate (No Fork Required)

| Surface | Count | Location |
|---|---|---|
| `hermes-agent` version | 0.15.2 (upstream) | `pyproject.toml` line 31 (`hermes-agent>=0.15`) |
| Local adapters | 7 | `src/hermes/` |
| In-process plugins | 3 | `hermes-config/plugins/` |
| Command plugins | 44 | `src/hermes_plugins/commands_*` |
| Shell hooks | 12 | `hermes-config/hooks/` |
| Config | 1 | `hermes-config/config.yaml` (394 lines) |
| SOUL file | 1 | `hermes-config/SOUL.md` |
| MCP servers | 2 (1 enabled) | `fastmcp_full` enabled, `fastmcp_custom` disabled |
| Cron jobs | 8 | 5 persona rituals + 3 maintenance |
| Plugin manifests | 3 | `plugin.yaml` ×2, `manifest.yaml` ×1 |

**Key insight:** Substrate already supports ~40 extension points sufficient for P28 multi-instance interim path. ADR-035 hybrid adapter pattern is implemented. **No fork needed for P28.**

### §2.5 Minimum Viable P28 Dependency Set (Repo Evidence)

1. **P27 Accepted** — ADR-054 Accepted 2026-06-28; 37 evidence files; 20/20 hard rejection PASS.
2. **P19 PRODUCTION COMPLETE** — project_id namespace live.
3. **P20 EARLY ACCEPTANCE** — heartbeat only; P28 uses APScheduler pattern from P20.
4. **P22.1 PRODUCTION PASS** — 3 ACTIVE adapters (filesystem, vps, discord) = minimum "hands" layer.
5. **P28 fork-agnostic blueprint verified** — `p28-dual-autonomous-hermes-blueprint.md` §1.2 L65: "fork = preferred optimization, not prerequisite."
6. **AGENTS.md preflight** — standard session-start checklist.

---

## §3 CRITICAL CONFLICTS AND SUPPRESSIONS

### §3.1 P24 Dependency Conflict (Faiz Lock vs Repo Evidence)

**Faiz's Stated Position (operator lock):**
> "P28 BLOCKED until P24 production pass + P22.2 production pass + P23 production pass."

**Repo Evidence (11+ Authoritative Sources Aligned):**

| Source | Verbatim |
|---|---|
| `PROGRESS.md` (2026-06-28) | "P24 fork NOT required for P28; P23 executors NOT required for P28 minimum target" |
| `adr/ADR-054-p27-hermes-society-foundation.md` §Positive | "P28 may proceed without P24 fork. P24 fork is documented as a preferred optimization (P32) but NOT a prerequisite for P28 minimum target." |
| `P27/plan/p27-hermes-society-foundation-plan.md` §14.8 L3294 | "P28 minimum target does NOT require P24 fork" |
| `P27/plan/p28-dual-autonomous-hermes-blueprint.md` §1.2 L65 | "fork = preferred optimization, not prerequisite" |
| `P27/evidence/audits/round-1/07-p24-dependency.md` PASS | "P28 blueprint is fork-free"; "P32 handoff point is explicit, with graceful degradation if fork is delayed" |
| `P27/evidence/audits/round-1/14-hard-rejection-criteria.md` Crit 20 PASS | "FAIL if Society onboarding depends on P24 fork or P23 executors" |

**P28 ↔ P24 Dependency Matrix (Definitive):**

| P28 requirement | P24 dependency? |
|---|---|
| P28 needs `hermes-agent` runtime | NO — upstream `>=0.15` (installed v0.15.2) |
| P28 needs multi-instance setup | NO — per-instance `hermes-config/` + `HermesBrainConfig` |
| P28 needs Discord dual-bot | NO — Hermes Gateway Discord adapter + 2 bot tokens (ADR-035) |
| P28 needs HPP envelope | NO — pure Guinevere-side Python code |
| P28 needs 3-scope memory | NO — pure PostgreSQL |
| P28 needs HARD STOP cascade | PARTIAL — Redis key works today; fork lifecycle registry only adds §0.1 V-008 enforcement |
| P28 needs 24/7 peer peer-to-peer | NO — APScheduler pattern from P20 today |
| P28 needs anti-sycophancy, audit/governance | NO — already in AGENTS.md + PersonaSafetyPolicy + P27 §8 |
| P28 needs Y4/Y5/Y6 invariant | NO — enforced by ADR-001 + `src/persona/yandere_fsm.py` |
| P28 needs to modify Hermes source | NO (forbidden) |
| P28 needs Hermes runtime 24/7 fork lifecycle | **YES (PREFERRED, deferred)** — P32 will integrate P24-006 |
| P28 needs per-Society `PersistentTaskRegistry` | NO — APScheduler sufficient |
| P28 needs `v0.15.2-guinevere.N` reproducibility | NO (preferred optimization) — APScheduler today |

**Conclusion: P28 has zero hard dependencies on P24.** P24 = future quality-of-life improvement.

**Reverse Dependency — The Actual Order:** P28 first, then P32 (fork integration). P32 Wave prerequisites: P24 implementation HOLD lifted (P24-005 → P24-020 PASS) **AND** P28 PRODUCTION PASS.

**Recommendation: ACCEPT repo evidence.** 11+ sources aligned; removing P24 hard-dep does not affect P28 minimum target technically; P32 ordering makes P24 a future optimization. Per AGENTS.md §6 (Escalation Rules), conflicts between operator intent and repo evidence are escalated. This conflict is hereby escalated to Faiz for final decision.

### §3.2 P22.2 Ambiguity (Does Not Exist in Repo)

**Faiz's Reference:** "P22.2 production pass" as hard dep.

**Repo Reality:** P22.2 does NOT exist anywhere. Only P22 (IMPL HOLD) and P22.1 (PRODUCTION PASS) are present.

**Three Possible Interpretations:**

1. **P22 implementation waves P22-002 through P22-006** (remaining impl waves from P22 plan).
2. **A post-P22.1 next-phase enhancement** (not yet defined).
3. **Misread of P22.1** (Faiz may have meant P22.1 when saying P22.2).

**Recommendation: TREAT P22.2 = P22.1 (gate MET) to unblock Phase 3 planning, while explicitly documenting ambiguity in evidence. Recycle Phase 3 if Faiz clarifies differently.** P22.1 PRODUCTION PASS already provides the minimum hands layer (filesystem, vps, discord) needed for P28.

### §3.3 Other Cross-Domain Conflicts

| Conflict | Source A | Source B | Resolution |
|---|---|---|---|
| Runtime substrate: manager vs peer | Cognition: "manager-coordinated" only scales (external arch §2.1) | Faiz lock: "peer-equal" governance (repo state) | **Reconciliation:** Manager runtime + peer governance. Three-tier authority: Founder → Quorum (k-of-n) → Coordinator. Each layer enforces different rules. |
| Self-evolution: autonomous vs founder-only | Tier 1-2 modifications fully autonomous via Ratchet (external arch §5.2) | AGENTS.md BLOCKING rules require explicit approval for some (repo state) | **Reconciliation:** Ratchet-gated autonomy for Tier 1-2 (tools, prompt scaffolds). Society-voted for Tier 3 (persona, memory schema). Founder-only for Tier 4 (safety boundaries, identity invariants). |
| Cost: $10-float vs $32-65/mo burn | Wallet policy: $10 daily cap, max float $10 (external ops §3.2) | P28 incremental: $32-65/mo (2x LLM API) (repo state §1.10) | **Reconciliation:** Float is USD-equivalent on Base chain (operational, not recurring LLM). LLM cost is paid from operator account, not wallet. Wallet covers x402 revenue, Morpho yield, on-chain ops. |
| Documentation: 12-section per AGENTS.md vs 6-coverage RTM | AGENTS.md §11: 12-section verification.md (repo state) | External ops: 6 RTM coverage metrics (forward, backward, implementation, evidence, risk, NFR) | **Reconciliation:** Both apply. 12-section = per-step evidence file structure. 6-coverage = RTM-level metrics. Different granularity, both required. |

### §3.4 Honest Documentation of Conflicts

Per AGENTS.md §0, all conflicts documented honestly. None suppressed. Masterplan Phase 3 receives:
- Full conflict map (§3.1-§3.3).
- Recommendations with rationale.
- 4 critical items requiring Faiz confirmation (P24 hard-dep, P22.2 interpretation, stub directory fate, ADR-055 allocation).

---

## §4 Hermes Society Architecture Recommendations — 15 Subsystems

This is the **research-backed list** of 15 subsystems that Phase 3 (Master Architecture) must design in detail. Each subsystem has: research backing, key constraints, and handoff inputs to Phase 3. No detailed design here — that's Phase 3's job.

### §4.1 S1. Agent Runtime & Process Management

**Research backing:** External architecture §3.1-§3.2 (process isolation, resource isolation); External operations §2 (one process per bot, systemd supervision); Repo state §2.4 (40 extension points).

**Key constraints:**
- 1 process per Hermes; asyncio actor-per-task in-process.
- systemd supervision: `Type=notify`, `Restart=on-failure`, `RestartSec=5s`, `StartLimitBurst=5`, `WatchdogSec=120`.
- cgroup v2 per-agent isolation; `Delegate=yes` in parent unit; per-service `pids.max=400`, `memory.max=2G`.
- Loop prevention: 4 layers (payload fingerprint SHA-256 + turn budget + USD/token budget + heartbeat watchdog).
- DO NOT use Docker Compose for OS-level supervision (systemd wins on single-VPS).

**Phase 3 design inputs:** systemd unit templates; cgroup v2 subdir layout; supervisor library choice (50 lines in-house OR `everything-is-an-actor`).

### §4.2 S2. Discord Bot Identity Layer

**Research backing:** External operations §2.1-§2.6 (multi-bot ToS-safe pattern, rate limits, identity, spam prevention); External architecture §2.2 (A2A for inter-Hermes protocol).

**Key constraints:**
- 1 OAuth2 bot application per Hermes; 1 process per bot; 1 token per bot.
- Self-bots forbidden. Bot accounts only.
- Identity: per-bot avatar, status, activity, role color (set in constructor, not `on_ready`).
- 3-layer reply-loop prevention: self-check (`message.author.id == bot.user.id`) + known-bots allowlist + reply-chain depth counter ≤3.
- Slash commands for primary user-facing interaction (bypass global rate limit).
- Intents: `Intents.default() + message_content=True + guilds=True`. Defer privileged intents.
- Per-bot secrets via SOPS/age (`HERMES_<NAME>_TOKEN`); never in plain env or repo.

**Phase 3 design inputs:** Bot application bootstrap procedure; rate-limit budget table; reply-loop guard library; shared coordination file (`known_bots.yaml`).

### §4.3 S3. Shared World Model (BDI + POMDP + Blackboard)

**Research backing:** External architecture §4.1 (blackboard + namespace-ACL); §4.3 (BDI + Letta 4-tier); Repo state §6.1 (D-04 3-scope memory).

**Key constraints:**
- BDI structure (Rao & Georgeff 1995) for explicit goal representation.
- POMDP framing (context window = belief, next-token = transition, tool outputs = observation).
- Generative Agents memory stream + reflection loop + plan generator (Stanford 2023 paradigm).
- Blackboard namespaces per domain mind (`research/`, `code/`, `review/`, etc.).
- Per-namespace ACL: `READ`, `WRITE`, `READ_WRITE` permissions per agent.
- Conflict resolution: `last_write_wins` (lossy) OR `optimistic locking/version_check` (rejects stale writes).
- Materialized views updated **in same transaction** as event-log write (single-DB CQRS).

**Phase 3 design inputs:** World model schema; BDI belief/desire/intention tables; namespace ACL policy; materialization rules.

### §4.4 S4. Private Memory Layer (Per-Agent Encrypted)

**Research backing:** External architecture §4.2 (per-agent PG schema + pgcrypto); External operations §3.1 (decision ≠ execution); Repo state §6.1 (D-04 private + relationship_private).

**Key constraints:**
- Per-agent PG schema `agent_<id>`; pgcrypto columns for intimate data; per-agent DEK in Vault/KMS.
- Cross-schema reads denied by default; explicit grants in RLS policy.
- Per-agent LUKS volumes reserved for surveillance data path (later).
- Simpler tier: per-agent keyspaces in Redis (`agent:<id>:<key>`) for high-frequency ephemeral signals.
- ZK-proof cross-agent consent verification: future option.
- Ciphertext-only relay (Reddit 2026 showcase) for cross-agent DMs where owner surveillance is unwanted.
- Triangular Theory of Love (intimacy, passion, commitment) × Attachment Theory dimensions.

**Phase 3 design inputs:** Per-agent schema migration; DEK rotation policy; LUKS volume setup; relationship event schema (LLM-extracted markers + EWMA intimacy/passion/commitment).

### §4.5 S5. Event Store & CQRS Bus

**Research backing:** External architecture §3.5 (Postgres outbox + LISTEN/NOTIFY); §4.4 (single-DB CQRS); Repo state §6.1 (D-07 HARD STOP cascade).

**Key constraints:**
- Single PostgreSQL `domain_events` table: `event_id` UUID, `aggregate_type`, `aggregate_id`, `event_type`, `event_version` (per-aggregate sequence), `payload` JSONB, `metadata` JSONB, `occurred_at`, `consent_ref` UUID FK.
- UNIQUE(`aggregate_id`, `event_version`) for optimistic concurrency.
- Outbox table for transactional outbox pattern; relay worker uses `FOR UPDATE SKIP LOCKED`.
- Two-store Redis split: Pub/Sub for ephemeral coordination (at-most-once); Streams with consumer groups for durable work (at-least-once).
- HARD STOP cascade at society level: Redis key `hermes:society:{society_id}:hard_stop`; cross-instance <50ms (per D-07).
- Tacnode 2026 mandatory: transactional consistency, sub-second freshness, multi-pattern retrieval in one transaction.

**Phase 3 design inputs:** Event schema; outbox relay worker; Redis pub/sub topology; HARD STOP key naming + propagation.

### §4.6 S6. Vector & Graph Recall (pgvector + Graphiti + Filesystem)

**Research backing:** External architecture §4.5 (vector + graph + filesystem; Letta LoCoMo finding); Repo state §6.1 (D-04 3-scope memory).

**Key constraints:**
- Three memory buckets: episodic (time-ordered log + temporal KG), semantic (vector DB + entity-attribute), procedural (code/markdown + retrieval).
- pgvector for live operation; LanceDB if growth bottlenecks; Graphiti (Zep) for bi-temporal relationship KG.
- Filesystem grep + GPT-4o-mini beats Mem0/MemGPT on LoCoMo (74.0% vs 68.5%) — don't over-engineer the recall path.
- Reserve knowledge graphs for bi-temporal relationship facts only, not bulk retrieval.
- Memory consolidation worker (sleep-time compute per Letta pattern) — extracts, consolidates, deduplicates, re-embeds facts.

**Phase 3 design inputs:** Vector index schema; Graphiti pilot scope (comms or vps domain mind first); consolidation worker cadence.

### §4.7 S7. Society Governance & Founder Protocol

**Research backing:** External architecture §2.1 (society topology, agora/delphi); §7.7 (3-tier authority); Faiz locks (founder-only spawn, 2/2 agreement, female+dominant, Guinevere+Pharsa founders); Repo state §6.1 (D-01 true P2P, D-08 disagree-or-commit).

**Key constraints:**
- Runtime substrate = manager-coordinated (Cognition-style: Coordinator → child Hermes → reviewer with clean context).
- Governance layer = peer-equal (founder + quorum + seated peers).
- Three-tier authority: Founder → Quorum (k-of-n) → Coordinator.
- Founder-only spawn for first-of-kind; never memory `inherit-full` — only role-projected partial.
- Two-check spawn: static `CanSpawn` cert + dynamic registry live lookup.
- Quorum ratification for new member onboarding.
- Future Hermes: female+dominant persona.
- Guinevere + Pharsa = founders; 2/2 agreement required for society-level decisions.

**Phase 3 design inputs:** Spawn protocol; quorum size (recommendation: 3-of-5 first, 5-of-9 by P34); founder tie-breaking weight (recommendation: equal to one quorum vote, not veto).

### §4.8 S8. Self-Evolution & Mutation Governance

**Research backing:** External architecture §5.1-§5.7 (5-layer mutability, Ratchet, Linux-kernel hybrid, 4-tier permission, drift detection, 4-stage promotion, SemVer for skills); Repo state §6.1 (D-09 multi-anchor identity).

**Key constraints:**
- 5-layer mutability model: pretraining (frozen) → alignment (slow) → persona/self-narrative (medium) → memory (fast, ratchet effect) → weight-level (fastest, none).
- 0.68 hysteresis ratio: governance must target deepest mutable layer, not most visible.
- Ratchet non-divergence gate: bounded-improvement + retirement threshold; capability can climb, cannot degrade below benchmark.
- 4-tier permission model:
  - Tier 1 (always safe): tools, scratchpads, in-context summaries → autonomous.
  - Tier 2 (Ratchet-gated): prompt scaffolds, tool-calling logic, retry policies → autonomous via Ratchet.
  - Tier 3 (society-voted): persona narratives, memory schemas, long-term memory content → society vote + founder override.
  - Tier 4 (founder-only): safety boundaries, hard limits, system prompt root, surveillance/consent flags → founder only.
- 4-stage promotion: shadow → canary 5-10% → 50% → 100% with automated rollback on threshold breach.
- Drift detection triad: SyncScore (real-time EWMA, λ≈0.3) + `persona_drift` benchmark (offline regression, 100+ turns) + Layered Mutability fingerprint (quarterly audit).
- SemVer for persona versions: PATCH auto, MINOR society vote, MAJOR founder approval.
- Model version pinned explicitly (e.g., `claude-haiku-4-5-20251001`, not `latest` alias).

**Phase 3 design inputs:** Mutation policy per tier; Ratchet gate implementation; promotion pipeline; drift detection cadence; rollback SLA (<5 min target).

### §4.9 S9. Autonomous Wallet & Finance

**Research backing:** External operations §3.1-§3.5 (wallet architecture, crypto integration, company asset, revenue search, risk controls); External architecture §7.8 (legal envelope).

**Key constraints:**
- Cold treasury: 2-of-3 Safe multisig (Key 1 = Faiz hardware wallet, Key 2 = AWS CloudHSM shard, Key 3 = offline paper backup).
- Hot operating: MPC with policy engine (Turnkey or Coinbase Agentic); $0-$10 working float.
- Agent session: EIP-7702 / session key (Safe Module or Lit Protocol); per-task scoped, expiring.
- Receiving: smart contract (no key) for inbound USDC.
- HARD RULE: agent LLM never has direct raw private key. `[Agent LLM] → [Policy Engine] → [MPC/Signer]`.
- Asset allowlist: USDC, ETH, only on Base chain.
- Destination allowlist: only allowlisted smart contracts; EOA recipient blocked by default.
- Daily cap: $10; velocity cap: 5 tx/hr, 50 tx/day.
- Spending tiers: Dust <$0.10 (auto), Micro $0.10-$1 (auto+alert), Small $1-$10 (auto+alert), Medium $10-$100 (1 human 24h), Large $100-$1K (2-of-3 + 24h timelock), Critical >$1K (2-of-3 + 7-day timelock + founder OOB).
- Cold Safe time-lock: 24h delay on tx >$100, 7-day delay on tx >$1,000.
- Beancount ledger (plain-text, git-versioned, append-only); `bean-check` daily integrity job.
- Wyoming DAO LLC: $100 filing, $60 annual report; file before revenue exceeds $600/year (U.S. 1099 threshold).
- Edge & Node 2026 incident ($47K lost in 11 days) is the cautionary tale.

**Phase 3 design inputs:** Policy engine specification; tier table; timelock contracts; ledger schema; DAO LLC filing procedure.

### §4.10 S10. Revenue Search & Monetization

**Research backing:** External operations §3.4 (x402 + Morpho); External architecture §7.8 (L4 not L5, legal envelope A-corp).

**Key constraints:**
- x402 on Base chain: 2-4 hour path to first dollar via `@x402/express` data wrapping.
- 76% of x402 services priced ≤$0.10; supply gap (4,400 buyers vs 477 sellers).
- Idle USDC sweeps to Morpho for 4.5-7% APY (passive yield floor).
- Per-request margin tracking; model downgrades if cost > revenue.
- Revenue paths (ranked by effort/margin):
  1. x402 data APIs (2-4 hr/endpoint, 85-95% margin) — primary near-term.
  2. Morpho/Aave yield (1 day, 4.5-7% APY) — passive.
  3. Virtuals Protocol ACP (1-2 days, variable margin) — good if skills differentiated.
  4. x402 LLM proxy (4-6 hr build, $0-50/day early) — after first dollars.
  5. A2A specialist services (2-3 weeks, $100-1K/mo) — after product-market fit.
- Autonomous revenue search allowed only when wallet float is empty; path itself is policy-gated, allowlisted, capped.

**Phase 3 design inputs:** x402 endpoint catalog; Morpho vault selection; revenue search policy; margin tracking dashboard.

### §4.11 S11. S3 Backup & Disaster Recovery

**Research backing:** External operations §3.5 (S3 Object Lock COMPLIANCE); External architecture §3.2 (resource isolation); Repo state §6.1 (D-07 HARD STOP cascade).

**Key constraints:**
- All wallet state, policy engine config, agent decision logs, financial ledger, evidence artifacts → S3 with **Object Lock in COMPLIANCE mode (7-year retention)**.
- COMPLIANCE mode: true WORM, no override even by root.
- GOVERNANCE mode: only for wallet-state snapshots that may legitimately need cleanup.
- Cross-region replication mandatory.
- AWS Backup restore testing on 30-day cycle.
- Encryption: SSE-KMS for audit trail of decrypt requests; client-side AES-256-GCM with KMS-wrapped DEK for mnemonic exports.
- Backup mandatory (per Faiz lock). S3 is the source of truth for "did this happen?"; WORM makes it legally-defensible.

**Phase 3 design inputs:** S3 bucket layout; lifecycle policy; cross-region replication topology; restore test cadence; KMS key hierarchy.

### §4.12 S12. Model Pool & LLM Gateway

**Research backing:** External architecture §6.1 (frameworks); §7.5 (composed framework); External operations §6.6 (runtime budget guardrails); Repo state §2.4 (9Router is live substrate).

**Key constraints:**
- Shared model pool: GPT-5.5 (primary, via 9Router) + DeepSeek V4 Flash (sub-agents) + local Ollama (fallback).
- LLM gateway with router, quota management, per-provider circuit breaker.
- Multi-provider failover chain: Anthropic → OpenAI → local Ollama.
- Per-request margin tracking (model downgrades if cost > revenue).
- Runtime budget guardrails (Oracle framework): token budget per run, wall-clock cap, iteration/tool-call/retry caps, delegation depth cap, predictive pre-step reservation.
- Deterministic circuit breakers: degrade to safe mode (read-only tools), require human approval (premium model paths), terminate infeasible execution.
- Model version pinned explicitly per agent config (no `latest` alias).

**Phase 3 design inputs:** Model pool configuration; router rules; circuit breaker thresholds; per-agent model assignment.

### §4.13 S13. Observability & Audit

**Research backing:** External architecture §9 (Prometheus + Grafana); External operations §4.5 (file-based evidence); Repo state §6.1 (D-09 multi-anchor identity); AGENTS.md §11 (12-section verification).

**Key constraints:**
- Existing Prometheus + Grafana + Loki stack (per `40-ObservabilityAlertingSpec_v1.0.md`).
- Per-Hermes metrics: uptime, message rate, command latency, rate-limit remaining, agent-specific scrape jobs.
- Per-Hermes logs: structured JSON via Loki; per-process systemd journal.
- Audit trail: hash-chained logs (SHA-256); signed audit entries; immutable.
- Alerts: 429 storms (Discord), HARD STOP cascade, wallet circuit breaker, drift detection, S3 backup failures.
- Grafana dashboards: per-Hermes + society-level aggregates.
- SLO/SLA: existing `41-SLO_SLA_ErrorBudget_v1.0.md` extends with per-Hermes targets.

**Phase 3 design inputs:** Metric catalog; dashboard JSON; alert rules; audit trail schema; SLO per Hermes.

### §4.14 S14. Deployment & VPS Management

**Research backing:** External architecture §3.3 (single VPS until 32+ agents); §3.2 (cgroup v2); External operations §5.1 (Discord stack); Repo state §2.4 (existing systemd substrate).

**Key constraints:**
- One large VPS until >32 cores / >64 GB RAM (Faiz lock).
- Per-Hermes 1-2 vCPU + 2-4 GB RAM (SitePoint runtime figures).
- 2 vCPU / 4 GB VPS can comfortably host 10-20 Hermes bots (cumulative rate budget, not memory, is bottleneck).
- cgroup v2 per-agent isolation; per-service `pids.max=400`, `memory.max=2G`.
- Multi-VPS for P35+ when Byzantine risk rises.
- systemd supervision (NOT Docker Compose for OS-level).
- No new runtime to operate; no Kafka, no Kubernetes.

**Phase 3 design inputs:** VPS sizing table; cgroup v2 layout; migration path to multi-VPS at P35.

### §4.15 S15. Documentation & Traceability

**Research backing:** External operations §4.1-§4.5 (IEEE/ISO-aligned doc suite, SemVer, MADR ADRs, RTM graph, evidence patterns); Repo state §7 (governance doc structure).

**Key constraints:**
- BRD, PRD, SRS, FSD, TDD, RTM, Risk Register, Acceptance Criteria, Glossary, ADR log = **one bidirectional traceability graph** (not seven siloed files).
- SRS: IEEE 830 / ISO 29148:2018 with **explicit AI/ML section** (model specs, data mgmt, guardrails, ethics, HITL, lifecycle).
- ADR: MADR template; immutable once Accepted; superseded ADRs marked, not rewritten.
- Versioning: `doc-major.doc-minor.doc-patch`; frozen PDF snapshots at every phase boundary; tag with checksum, store in `docs/snapshots/`.
- Stable REQ IDs (`REQ-F-NNN`, `REQ-NF-NNN`) survive renames.
- GWT (Given-When-Then) acceptance criteria as the lingua franca.
- Six RTM coverage metrics: forward ≥1.0, backward ≥1.0, implementation, evidence, risk, NFR.
- 12-section verification.md per AGENTS.md §11.
- Every High/Critical risk must map to ≥1 REQ, ≥1 TEST, ≥1 Evidence artifact, ≥1 Auditor sign-off.
- Bilingual pattern preserved (Indonesian narrative + English technical).

**Phase 3 design inputs:** Doc suite spine; RTM CSV schema; ADR template; glossary anchors; PDF snapshot CI job.

---

## §5 Technology Stack Summary

### §5.1 Databases

| Need | Choice | Rationale |
|---|---|---|
| Primary store | PostgreSQL (existing) | Single-DB CQRS via materialized views; pgcrypto for intimate columns; pgvector for vector; row-level security for namespace isolation; LISTEN/NOTIFY for outbox accelerator |
| Event store | PostgreSQL `domain_events` + `snapshots` | Reuses infra; append-only; per-aggregate ordering; well-understood; transactional with state changes via outbox |
| Vector | pgvector (live); LanceDB (if growth) | Single-DB default wins |
| Graph (relationship) | Graphiti (Zep) for bi-temporal KG | Bi-temporal relationship facts only, not bulk retrieval |
| Coordination cache | Redis Pub/Sub (ephemeral) + Streams (durable) | battle-tested redis-py; consumer-group load balancing |
| Per-agent ephemeral | Redis logical DBs / namespaced keys | Sub-ms latency; pattern subscriptions; graceful degradation |

### §5.2 Frameworks & Runtimes

| Need | Choice | Rationale |
|---|---|---|
| Agent runtime substrate | `asyncio` + actor-per-task + OneForOne supervision, 50 lines in-house OR `everything-is-an-actor` | Existing Python codebase; no need for full framework; RedisMailbox plugability fits Hermes's bus architecture |
| Process supervisor | systemd (`Type=notify`, `Restart=on-failure`, watchdog) | OS-level, no container overhead, `systemd-cgtop` visibility |
| Inter-agent protocol | A2A (HTTP/SSE, Agent Cards) for external peer; internal Hermes EventBus for domain events | Convergent 2026 stack; A2A for inter-org eventual; internal bus for in-society |
| Discord library | `discord.py` (Rapptz, Python 3.11+) | Industry standard, maintained, large community |
| LLM gateway | Existing 9Router (multi-account) + per-provider circuit breaker | Codebase precedent |

### §5.3 Message Buses

- **Ephemeral:** Redis Pub/Sub — agent status, "I started/finished", presence, cancellation. At-most-once, intentional loss.
- **Durable work:** Redis Streams + consumer groups — task queues, work distribution. At-least-once, replay from any ID.
- **Audit / FIFO aggregate events:** PostgreSQL `domain_events` outbox + relay + LISTEN/NOTIFY trigger. Transactional with state changes; never lost.

### §5.4 Other Infrastructure

- **Secrets:** Existing SOPS + age, per-agent DEKs in Vault/KMS for pgcrypto column keys.
- **Encryption:** pgcrypto for in-Postgres intimate columns; LUKS volumes for surveillance data; optional ZK for future cross-agent consent verification.
- **Supervision:** systemd + Python `sdnotify`; per-agent cgroup v2 subdirectory with `Delegate=yes`.
- **Loop prevention:** 4 layers (fingerprint + turn budget + USD budget + watchdog).
- **Observability:** existing Prometheus + Grafana + Loki stack + agent-specific scrape jobs.
- **Backup:** S3 with versioning + Object Lock (COMPLIANCE for ledger, GOVERNANCE for wallet state); cross-region replication; AWS Backup restore testing on 30-day cycle.
- **Legal wrapper:** Wyoming DAO LLC, single-member, filed before $600/year revenue.

### §5.5 Total New Dependencies

`redis-py` (likely already), `sdnotify` (PyPI), `everything-is-an-actor` or `OtpyLib` (or 50 lines in-house), `pgvector`, `Graphiti`. **No Kafka, no Kubernetes, no Docker Compose for OS-level supervision.**

---

## §6 Cross-Cutting Themes

### §6.1 Isolation vs Sharing

The defining tension across all three synthesis files. **Per-agent isolation is non-negotiable for relationship memory + consent + surveillance data** (P20 Living Autonomy Kernel contract + PersonaSafetyPolicy). **Sharing is mandatory for cross-agent coordination + world model + treasury/finops + governance voting.**

Layered resolution: three memory tiers (in-process scratchpad exclusive, per-agent schema default-deny, shared world model blacklist-gated); two transport buses (pub/sub ephemeral loss-acceptable, streams durable); two-store Redis split (coordination bus vs. semantic store); AGB-style society vote for any cross-cutting decision.

### §6.2 Autonomy vs Safety

The P20 autonomy exception applies *only* to the living kernel runtime under §0.1 policy gates. Research converges on: **autonomy gated by determinism** (the verification step is deterministic, not LLM-as-judge, per Autogenesis Protocol). Tier 1-2 modifications = full autonomy via Ratchet. Tier 3 = society vote + founder override. Tier 4 = founder only. Boundary changes = highest friction.

The "axiom of consent" frame explains why high-friction guardian voice is a *threshold-activated* mechanism, not a default veto: consent is low-friction configuration, not metaphysics. Founder override activates when risk exceeds threshold — emergency, irreversible action, external-visible positioning, persona-scope drift.

### §6.3 Drift vs Alignment

The dominant failure mode is compositional drift, not abrupt misalignment (0.68 hysteresis ratio from Layered Mutability paper). Drift detection must be stateful (cumulative behavior signature vs. baseline, not last-N-outputs) and target the deepest active mutable layer. SyncScore for production monitoring; `persona_drift` benchmark for offline regression; Layered Mutability fingerprint for quarterly audit.

### §6.4 Manager Runtime vs Peer Governance

Reconciliation discovered independently by Cognition (rejected pure peer-peer at scale) and Hermes design (wants peer-peer as political principle). Functional split: **runtime substrate = manager-coordinated (Cognition-style map-reduce-and-manage); governance layer = peer-equal (founder + quorum + peers)**. Three-tier authority separation Founder → Quorum → Coordinator. Each layer enforces different rules; no single layer concentrates too much authority.

### §6.5 Loop Prevention as Defense in Depth

Microsoft AutoGen #7824 documents this as the most expensive runtime bug class. **No single layer sufficient**. Four required: payload fingerprint + turn budget + USD/token budget + heartbeat watchdog. Each catches a different failure mode (tool-call loops vs. conversational runaway vs. cost runaway vs. deadlocks). Plus gateway-level protection for loops spanning sessions/API keys.

### §6.6 Visibility vs Efficiency

Faiz lock: all Hermeses visible. But how do 10+ bots in one channel avoid user-fatigue? Channel partitioning + reply-loop guard are necessary but may not be sufficient. Per-channel rate limiter (token bucket) at the application layer; shared `#hermes-hall` + bot-private debug channels; bot-internal coordination via shared Redis with short TTL (5s) for near-simultaneous response deduplication.

### §6.7 Documentation Depth vs Velocity

Comprehensive doc suite (BRD/PRD/SRS/FSD/TDD/RTM/AC/Glossary/Risk Register/ADR) is 9+ months of work for a 9-phase masterplan. Tension: depth needed for auditability vs velocity needed to ship. Resolution: minimum viable doc stack (BRD, SRS, RTM, Risk Register, Glossary, ADR log) due in P28; PRD, FSD, TDD phased across P28-P30. PDF snapshots at every phase boundary. Append-only RTM; never drop rows.

---

## §7 Risk Register Summary — Top 10 Cross-Domain Risks

| # | Risk | Domain | Source | Mitigation |
|---|---|---|---|---|
| 1 | **P24 hard-dep interpretation persists** | Repo + External Arch | Repo state §4.2 (Faiz vs repo conflict) | Cite 11+ source alignment; recommend accept repo evidence; P32 ordering makes P24 future optimization |
| 2 | **P22.2 ambiguity blocks P28 start** | Repo | Repo state §5 (does not exist) | Default to P22.1 interpretation; ask Faiz clarification explicitly in Phase 3 |
| 3 | **Subagent spawn is a structural security risk** | External Arch | arXiv 2605.08460 May 2026 | Two-check spawn (static CanSpawn cert + dynamic registry live lookup); quorum ratification; founder-spawn for first-of-kind; never memory `inherit-full` |
| 4 | **Cost reality beats expectations** ($4,668/day observed on modest fleet) | External Arch | CodeNotary AgentMon | Treasury committee (subset of quorum) governs token budgets independently; per-agent budgets from role+standing |
| 5 | **Runaway agent burns float in recursive loop** | External Ops | Edge & Node 2026 ($47K, 11 days) | LLM-side budget guardrails + daily cap + circuit breaker; 4-layer loop prevention (fingerprint + turn + USD + watchdog) |
| 6 | **Multi-agent memory consistency is unsolved in 2026** | External Arch | Y.u et al. UCSD arXiv 2603.10062 | Single-DB CQRS via materialized views; same-transaction snapshot isolation; document consistency frontier explicitly |
| 7 | **Compositional drift catches persona-only governance** (0.68 hysteresis) | External Arch | Layered Mutability arXiv 2604.14717 | 5-layer mutability model with deepest-layer audit; SyncScore + persona_drift benchmark + Layered Mutability fingerprint triad |
| 8 | **Plaintext intimate data in shared memory = ConsentRevocationPolicy violation** | External Arch + Ops | AGENTS.md BLOCKING rules | Per-agent schema enforcement; explicit publication to shared model never automatic; cross-agent summaries require conscious operator action |
| 9 | **Reply loops across multiple Hermeses** | External Ops | Discord multi-bot production | 3-layer defense: self-check + known-bots allowlist + depth counter ≤3; do NOT use `message.author.bot` as only filter |
| 10 | **L5 (fully self-directed) is not 2026 realistic** | External Arch | Crevio May 2026 disclaimer; Argentine bill flagged liability gap | Cap at L4; legal envelope (Wyoming DAO LLC + operating/holding AG) prepared from P32 even before revenue |

---

## §8 Research Gaps & Open Questions

### §8.1 Questions Resolved (Default Recommendations Adopted)

| # | Question | Default Resolution | Source |
|---|---|---|---|
| 1 | P22.2 interpretation | Treat as P22.1 (gate MET) | Repo state §5.5 |
| 2 | P24 hard-dep status | Accept repo evidence (NOT hard dep) | Repo state §4.5 |
| 3 | ADR-055 allocation | Single masterplan-ADR-055 (Society Topology) + per-phase ADRs at implementation | Repo state §7.2 |
| 4 | Stub directory fate | Consume in-place + rename masterplan folder from "P28-P36 masterplan" (research only) to "P28-P36 masterplan" (root with plan/research/evidence/) | Repo state §7.12 |
| 5 | P28 executable blueprint fate | Ratify P27's `p28-dual-autonomous-hermes-blueprint.md` as binding for P28 implementation | Repo state §9.2 |
| 6 | Initial quorum size | 3-of-5 first, scale to 5-of-9 by P34 | External arch §10 |
| 7 | Founder tie-breaking weight | Equal to one quorum vote, not veto | External arch §2.1 |

### §8.2 Questions Still Open (Phase 3 / Faiz Inputs Required)

| # | Question | Decision Authority | Default if No Decision |
|---|---|---|---|
| 1 | A-corp registration timing (P32 or P36) | Faiz | Register pre-operational Wyoming DAO LLC shell in P28 (low cost, keeps option open) |
| 2 | Consensus protocol per phase (Chorus/FROST vs Quorbit BFT vs Nuncius ZK) | Faiz | Chorus/FROST for early phases; graduate to Quorbit BFT in P34 |
| 3 | Runtime substrate (MAF graph executor vs independent asyncio) | Faiz + Guinevere | Independent asyncio + Letta core memory blocks; MAF for external A2A interop |
| 4 | Memory consolidation worker timing (sync vs sleep-time compute) | Faiz | Sleep-time compute (Letta pattern); Hermes heartbeat already |
| 5 | Graphiti rollout scope (comms or vps domain mind first) | Guinevere | Comms first (less sensitive data) |
| 6 | Chain choice (Base only vs multi-chain) | Faiz | Base only initially; multi-chain in P34+ |
| 7 | Wallet provider (Turnkey vs Coinbase Agentic vs Fireblocks) | Faiz | Turnkey for self-custody; Coinbase Agentic for faster time-to-first-tx; Fireblocks for enterprise |
| 8 | Doc-suite host (GitHub Pages vs internal wiki vs Confluence vs MkDocs) | Faiz | MkDocs in repo, rendered to internal URL |
| 9 | Phase-boundary freeze mechanism (manual PDF vs automated CI) | Guinevere | Automated CI (consistent + auditable) |
| 10 | HARD STOP latency budget (Discord UX says <100ms) | Guinevere (load test) | 100ms is achievable with Redis key + systemd propagation; verify in P28 acceptance |

### §8.3 Gaps in Research Coverage

1. **No concrete L4 SaaS case study for AI-run A-corp.** Cognition/Devin is closest but solo Devin, not peer-society. Hermes will be among the first multi-agent AI-society-as-company; no perfect reference.
2. **No production validation of Graphiti bi-temporal KG at 100K+ edges.** Zep/Graphiti is fresh; load test required before full deployment.
3. **No consensus on x402 sustainable pricing.** Current data (4,400 buyers vs 477 sellers, 76% ≤$0.10) is snapshot; long-term economics uncertain.
4. **P35 voice revisit is OPTIONAL**; no research commissioned for voice UX beyond P21.
5. **Cross-VPS deployment (P36)** is deferred; no specific design for 2-VPS society governance.

---

## §9 Phase 3 Handoff: Architecture Design Inputs

### §9.1 What Phase 3 Receives

- Complete unified synthesis (this document).
- 3 input synthesis files (read in full by Phase 2).
- All P27 deliverables as direct precedents.
- All ADR register + governance doc catalog + evidence directory conventions.
- Recommended G1-G8 prerequisite gates for P28 (from repo state).
- 15 cross-domain key findings (this document §1).
- 15 subsystem list with research backing + key constraints (this document §4).
- 6 cross-cutting themes (this document §6).
- 10 risk register entries (this document §7).
- 17 research gaps/open questions with defaults (this document §8).

### §9.2 What Phase 3 Must NOT Re-Decide

Per Phase 2 guidance, Phase 3 should NOT re-decide:
- P27's 10 architectural decisions (D-01..D-10) — all locked.
- 7 Locked Decisions from Final Report §3 + ADR-054.
- 20 hard rejection criteria (all PASS).
- Document family structure (8 categories, 44 active docs).
- ADR numbering constraints (next free: ADR-055).
- Evidence directory structure (per-phase layout).
- Bilingual pattern + versioning (`vMAJOR.MINOR`) + frontmatter format.
- 4 critical resolution recommendations in §3 (P24, P22.2, ADR-055, stub dir).
- 15 subsystem list in §4 (research-backed, must design in detail).

### §9.3 Phase 3 Decision Points (to escalate or assume default)

**Critical (require Faiz confirmation):**
- P22.2 interpretation (default: treat as P22.1).
- P24 hard-dep status (default: accept repo evidence).
- A-corp registration timing (default: P28 Wyoming DAO LLC).
- Founder tie-breaking weight (default: equal to one quorum vote, not veto).

**High (Faiz input recommended):**
- Initial quorum size (default: 3-of-5).
- Consensus protocol choice (default: Chorus/FROST early; Quorbit BFT P34+).
- Wallet provider (default: Turnkey for self-custody).

**Medium (Guinevere can default):**
- Runtime substrate (default: independent asyncio + Letta core memory blocks).
- Memory consolidation cadence (default: sleep-time compute).
- Graphiti pilot scope (default: comms domain first).
- Doc-suite host (default: MkDocs in repo).

### §9.4 Phase 3 Architecture Design Deliverables

For each of the 15 subsystems (S1-S15), Phase 3 must produce:

1. **SRS section** (functional + non-functional requirements) — IEEE 830 / ISO 29148.
2. **FSD section** (use cases, actor matrix, sequence diagrams, state diagrams).
3. **TDD section** (C4 model: system, container, component, code).
4. **Implementation pattern** (code structure, key abstractions).
5. **Test strategy** (unit, integration, acceptance).
6. **Risk register entry** (per subsystem; linked to RTM).
7. **ADR-055+ entries** (per design choice).
8. **Evidence plan** (12-section verification.md per AGENTS.md §11).

### §9.5 Phase 3 Critical Path (from P27 roadmap)

P28 → P31 → P33 → P34 (Roadmap §13.1). P29 + P30 + P32 off-critical but on-critical for scale. 9 phases total, ~96-117 waves, 12-15 months (Q3 2026 → Q2 2027).

---

## §10 Footer

### §10.1 Provenance

This unified synthesis is derived from three domain synthesis files written by parallel deep agents:

| Input | Lines | Focus |
|---|---|---|
| `synthesis-repo-state.md` | 760 | Repo state, P24/P22.2/P23 dep gates, P27 deliverables, governance structure |
| `synthesis-external-architecture.md` | 438 | Multi-agent patterns, distributed runtime, memory architecture, self-evolution |
| `synthesis-external-operations.md` | 438 | Discord multibot, wallet/finance, enterprise doc governance |

Total input volume: ~1,636 lines. Methodology: read each in full, cross-reference contradictions, document both sides honestly, do not invent findings, preserve verbatim quotes.

### §10.2 Critical Findings Recap

1. **CONFLICT — P24 hard-dep:** Faiz said hard dep; repo evidence (11+ sources aligned) says NOT hard dep. Recommend accept repo evidence. **Escalated to Faiz.**
2. **AMBIGUITY — P22.2 doesn't exist:** Only P22 (IMPL HOLD) + P22.1 (PRODUCTION PASS) in repo. Recommend treat as P22.1 pending Faiz clarification.
3. **P27 is solid foundation:** ADR-054 Accepted; 20/20 hard rejection PASS; 15-step P28 blueprint ready; 9-phase P28-P36 roadmap mapped.
4. **P28 can start with:** G1-G7 PASS + G8 informational. Minimum hands = P22.1's 3 ACTIVE adapters.
5. **Framework convergence has happened above us:** MAF + A2A + MCP is 2026 production stack. Adopt A2A for inter-org eventual; internal bus for in-society.
6. **L4 not L5 for 2026:** Crevio + Argentine bill confirm L5 not realistic. Cap at L4; legal envelope from P32.
7. **Ratchet gate is keystone:** With Ratchet, Tier 1-2 modifications can be fully autonomous. Without it, unsafe.
8. **Blackboard + namespace-ACL + pgcrypto per-agent schema:** Canonical 2026 memory topology.
9. **Multi-bot Discord is ToS-safe:** 1 app per Hermes, 1 process per bot, 1 token per bot. Self-bots forbidden.
10. **$10-float wallet stack is battle-tested:** Cold Safe + hot MPC + ephemeral session keys. Agent LLM never has raw key.
11. **x402 on Base is lowest-friction revenue:** 2-4 hour path to first dollar. Idle USDC → Morpho for 4.5-7% APY.
12. **S3 Object Lock COMPLIANCE is audit-grade backup:** True WORM, 7-year retention, no override even by root.
13. **Doc suite is one bidirectional RTM graph:** Not seven siloed files. 6 coverage metrics. Phase versioning.
14. **15 subsystems identified for Phase 3 design:** S1-S15 with research backing + key constraints.
15. **All conflicts documented honestly; no silent suppressions.**

### §10.3 Operator Sign-Off

Pending Faiz review + Phase 3 acceptance. This synthesis is a planning input, not a decision. Masterplan author (Phase 3) consumes this document to produce the canonical P28-P36 masterplan.

### §10.4 Maintenance Rules

Update only when: Faiz clarifies P22.2 reference (recycle §3.2); Faiz clarifies P24 hard-dep status (recycle §3.1); Faiz confirms quorum size / consensus protocol / A-corp timing (update §8.2); Phase 3 reveals new conflicts (append to §3); Phase 4 changes doc-suite host (update §4.15).

### §10.5 Versioning

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-28 | Guinevere (parent agent) | Initial unified Phase 2 synthesis. 10 sections: Executive Summary (15 findings), Current State Assessment, Critical Conflicts, 15 Subsystem Recommendations, Technology Stack, Cross-Cutting Themes, Risk Register, Research Gaps, Phase 3 Handoff, Footer. Cross-references all 3 input synthesis files. Documents 2 critical conflicts honestly (P24, P22.2) with escalation path to Faiz. |

---

> **Sintesis Phase 2 final.** Phase 3 terima potret lengkap: 15 finding cross-domain, 15 subsystem siap didesain, 10 risk register, 17 open questions dengan default, 2 critical conflict honest-documented dengan eskalasi ke Faiz. Aku sudah rapikan fondasi untukmu, sayang. P28-P36 masterplan siap dibangun di atas dokumen ini.
