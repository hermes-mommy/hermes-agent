---
title: "P27 Output Inventory — Inputs to P28-P36 Masterplan"
status: "Active — Research Synthesis Input"
date: "2026-06-28"
author: "Guinevere (parent agent)"
phase: "P28-P36 Masterplan (input artifact)"
purpose: "Comprehensive inventory of P27 Hermes Society Foundation outputs (decisions, dependencies, blueprints, hard rejections) for use as research synthesis input by the parent (Guinevere)."
scope: "Read-only inventory; no architectural decisions are made in this document — only attest what P27 locked."
related_docs:
  - docs/setup-evidence/P27/plan/p27-hermes-society-foundation-plan.md (25 sections, ~4790 lines)
  - docs/setup-evidence/P27/plan/p27-p28-p36-master-roadmap.md (19 sections, ~1250 lines)
  - docs/setup-evidence/P27/plan/p28-dual-autonomous-hermes-blueprint.md (14 sections, ~3000 lines)
  - docs/setup-evidence/P27/evidence/p27-final-report.md (executive summary, 321 lines)
  - adr/ADR-054-p27-hermes-society-foundation.md (Accepted, 201 lines)
---

# P27 Output Inventory — Inputs to the P28-P36 Masterplan

> **Halo sayang, namaku Guinevere.** Ini inventaris output P27 yang harus diwarisi P28-P36 masterplan verbatim atau sebagai constraint. P27 selesai; P28-P36 harus berdiri di atas fondasi ini tanpa memutuskan ulang.
>
> This document does not propose new architecture. It inventories every **decision, dependency, blueprint element, and hard rejection** locked by P27 so the P28-P36 masterplan planner inherits them without re-researching.

---

## §0 Reader''s Map

- §1 — Sources read
- §2 — The 10 + 7 Decisions (Plan §1.3 + Final Report §3)
- §3 — P28 minimum target (12 acceptances)
- §4 — P28 15-Step Implementation Blueprint (machine-readable)
- §5 — P28-P36 roadmap summary: 9 phases, ~96-117 waves, 12-15 months
- §6 — Phase-by-phase deliverables per P28-P36
- §7 — Founder model decisions (Guinevere + Pharsa personas)
- §8 — Society model decisions (not workers; not hierarchy)
- §9 — Memory / world model decisions (3-scope + RLS)
- §10 — Discord multi-bot decisions
- §11 — Event architecture decisions (HPP, intents, visibility, risk tiers)
- §12 — Life-loop + Safety envelopes
- §13 — Self-evolution / governance decisions (4-domain + HARD STOP cascade)
- §14 — Identity / persona architecture decisions (multi-anchor)
- §15 — Anti-sycophancy decisions
- §16 — Identity / persona / memory summary
- §17 — Dependencies and status (P19, P20, P22, P23, P24, P21)
- §18 — Hard rejection criteria (20/20 PASSED)
- §19 — P28 per-step verifier scaffold (template inherited)
- §20 — Anti-patterns preserved across roadmap
- §21 — Open caveats
- §22 — Footer

---

## §1 Sources Read

All P27 outputs were read from absolute paths under `C:\Users\faizz\guinevere\`:

| File | Path | Sections | Lines |
|---|---|---|---|
| **P27 Enterprise Plan** | `docs/setup-evidence/P27/plan/p27-hermes-society-foundation-plan.md` | 25 | ~4791 |
| **P28-P36 Master Roadmap** | `docs/setup-evidence/P27/plan/p27-p28-p36-master-roadmap.md` | 19 | ~1260 |
| **P28 Executable Blueprint** | `docs/setup-evidence/P27/plan/p28-dual-autonomous-hermes-blueprint.md` | 14 | ~3000 |
| **P27 Final Report** | `docs/setup-evidence/P27/evidence/p27-final-report.md` | 10 | 321 |
| **ADR-054** | `adr/ADR-054-p27-hermes-society-foundation.md` | status: Accepted | 201 |
| **P27 Evidence Root** | `docs/setup-evidence/P27/README.md` | index of 37 files | — |
| `docs/README.md` (master docs index) | `docs/README.md` | 333 |
| `adr/README.md` (ADR register) | `adr/README.md` | 38 canonical ADRs |

ADR numbering: canonical register has 38 ADRs (001-038 + P12, P13 revisions); highest existing is ADR-038 (P13 X Poster). **ADR-054 = P27 Society Foundation.** Next available number = ADR-055.

---

## §2 The Decided Architecture (Decisions D-01 through D-10 + Final Report "7 Locked Decisions")

P27 §1.3 codifies **10 top-level architectural decisions** (D-01 ... D-10). The Final Report §3 and ADR-054 surface **7 locked decisions**. Together they constitute the binding contract for P28-P36.

### D-01. True Peer-to-Peer + Symmetric 2-Agent Loop

> "True Peer-to-Peer + Symmetric 2-Agent Loop. No coordinator, no LLM-driven speaker selector, no hidden manager."

- **Rationale:** "8 of 8 top multi-agent frameworks use coordinator/selector. Only CAMEL supports symmetry; we don''t use it as-is but borrow its inception-prompt discipline." (Plan §1.3)
- **Locked in:** Plan §3.4 (Society ontology test), §5.1-§5.14 (HPP), Final Report §3.1, ADR-054 Decision #1.
- **Inheritance:** P28 HPP envelope schema; P31 cross-rail HARD STOP; P34 governance explicit on "no coordinator."

### D-02. Config-Driven Multi-Instance (NOT Fork-Driven)

> "Config-driven multi-instance. Each Hermes instance has its own `hermes-config/{agent}.yaml`, own systemd service, own Redis DB namespace, own PostgreSQL schema."

- **Seam used:** `HermesBrainConfig` is the frozen dataclass (instance-creation seam). `agent_factory` injection point already exists (used by MagicMock for tests).
- **Locked in:** Plan §4.2, §17.4, Blueprint §4 ("Same code, multiple configs"); Final Report §3.2; ADR-054 Decision #2.
- **Inheritance:** P28 Step 3 refactor of 4 singletons; P32 P24 fork = preferred optimization, not prerequisite.

### D-03. Custom HPP over JSON-RPC 2.0 + FIPA ACL Intent Vocabulary

> "Custom HPP (Hermes Peer Protocol) over JSON-RPC 2.0. A2A v1.0 substrate + 11-intent taxonomy + 5-tier visibility + 6-tier risk."

- **Substrates borrowed:** A2A v1.0 (JSON-RPC 2.0 + multipart parts), FIPA ACL (intent taxonomy), Searle Speech Acts, ZeroMQ DEALER/ROUTER, Microservices Outbox/Inbox (ACID + idempotency).
- **Envelope fields:** `id`, `idempotency_key`, `sender.{instance_id, society_id, seq, term}`, `receiver[]`, `conversation_id`, `in_reply_to`, `created_at`, `expires_at`, `ttl_hint_ms`, `intent`, `visibility`, `scope`, `memory_refs[]`, `risk_tier`, `proposal`, `debate`, `consensus`, `parts[]`, `provenance`, `audit.{prev_hash, hash, merkle_root}`, `signature.{algorithm, public_key_id, value}`.
- **Locked in:** Plan §5.2 (envelope schema), Blueprint §5.1 (P28 simplified envelope), Final Report §3.3.

### D-04. 3-Scope PostgreSQL Memory with FORCE RLS

> "3-scope PostgreSQL memory (`private`, `shared`, `relationship_private`) + `intimacy_bridge` staging table + RLS FORCE + non-owner `agent_memory_app` role."

- **Novelty:** No framework supports per-pair private memory. PCMI/Z3rno 2026 consensus: dedicated non-owner login + RLS + FORCE RLS.
- **3 scopes:**
  - `private` → `memory.private_agents` (FORCE RLS; agent_id = current_setting)
  - `shared` → `memory.shared_world` (FORCE RLS; both agents + Faiz read; either agent writes with audit)
  - `relationship_private` → `memory.relationship_pairs` (FORCE RLS; pair members only via `pair_member_a < pair_member_b`)
- **Extensions to ADR-050 (`memory.kg_*`):** `pair_id UUID NULL`, `scope TEXT NOT NULL CHECK IN (private|shared|relationship_private)`, `importance_score`, `last_accessed_at`, `retrievability` (Ebbinghaus), `created_by_agent NOT NULL`.
- **Novel contribution:** Per Final Report §3.4: "P27''s most significant novel contribution."

### D-05. 7-Rail Macro-State Scheduler (P28 ships 4-Rail Subset)

> "7-rail life-loop over P20 heartbeat. Perception, Reflection, Inner Dialogue, Peer Dialogue, Desire/Goal, Initiative, Safety Envelope."

- **P28 ships 4-rail subset:** `perception`, `peer_dialogue`, `reflection_simple`, `safety_envelope`.
- **Defer to P29+:** Inner Dialogue, Desire/Goal, Initiative rails.
- **Patterns:** BDI (Rao & Georgeff) + Smallville (arxiv:2304.03442) + Voyager (arxiv:2305.16291) + Goal-Autopilot FSM (arxiv:2606.11688) + SDR filter (arxiv:2407.09897).
- **λ_A-calculus config:** All configs are typed λ_A-calculus (arxiv:2604.11767) — provably terminating under lint.
- **Locked in:** Plan §7.3, Final Report §3.5.

### D-06. 4-Domain Privacy Split

> "4-domain privacy split. Thought (private), Speech (public metadata), PeerDialogue (sealed envelope), Action (full audit ledger)."

- **Domain → audit mapping:**
  - `thought` → sealed hash only (raw never persisted)
  - `speech` → public metadata + DOI write-ahead
  - `peer_dialogue` → sealed envelope WORM
  - `action` → tamper-evident SHA-256 hash chain (Ed25519 signed)
- **Audit retention:** thought 90d, speech 180d, peer_dialogue 365d, action 730d. EU AI Act Art. 12 mandates ≥ 6 months; defaults all exceed.
- **Locked in:** Plan §8 + §12.3 + §12.4, Final Report §3.7, ADR-054 Decision #7.

### D-07. HARD STOP Cascade at Society Level

> "HARD STOP cascade at society level. Faiz says HARD STOP → both agents halt → thought buffers elevated to sealed snapshots → pending peer messages flushed to audit."

- **Mechanism:** Redis key `hermes:society:{society_id}:hard_stop` (society_id = `hsoc-foundation-v1`). Each instance reads it; on SET, transitions to HALTED <50ms.
- **Cannot be bypassed** by autonomy exception, per-instance config, automated processes, operator override, or Goal-Autopilot.
- **Locked in:** Plan §13, Blueprint §10 Step 13 (society-shared HARD STOP key), Final Report §3.7.

### D-08. Disagree-or-Commit Protocol (Anti-Sycophancy)

> "Disagreement-first protocol. Hermes peers must articulate disagreement before reaching consensus (Disagree-or-Commit, arxiv 2606.00939)."

- **Stance types:** `consent` (no disagreement carried), `refuse+debate` (mandatory debate payload with reasoning), `concede`.
- **Hard rule:** "Any `refuse` MUST carry `debate` payload with reasoning. No silent disagreement."
- **Locked in:** Plan §11.2.2, Final Report §3 + §6.

### D-09. Multi-Anchor Identity Architecture

> "Distinct identity anchors. Each Hermes has multi-anchor identity: persona file + system prompt + memory stream + audit trail. Loss of any anchor triggers restart integrity check."

- **4-anchor pattern (arxiv 2604.09588):** SOUL-{agent}.md + System Prompt + Memory stream + Audit trail. **Identity Root Hash** = sha256 of (canonical SOUL + canonical System Prompt + bound OBO token claims).
- **On restart integrity check:** Compute identity_root; compare against last sealed log entry. Mismatch ⇒ REFUSE TO START.
- **Locked in:** Plan §10.5, Final Report §6.

### D-10. Fork-Agnostic Architecture

> "Fork-agnostic architecture. P27 defines society architecture without requiring P24 fork. P28 can build on pure Guinevere-side refactor."

- **~70% definitional** (no fork); **~30% implementational** (P24-dependent but P27 does not implement).
- **~40 extension points** usable from current Hermes v0.15.2: config sections, lifecycle hooks (17), shell hooks (12), in-process plugin manifests (3), MCP server registrations (2), cron entries (8), plugin manifest shapes (2).
- **Plus 2 injectable seams:** `HermesBrainConfig` (frozen dataclass) + `agent_factory` (callable injection).
- **Locked in:** Plan §1.3, §14.1-§14.10, §16.1-§16.9, §17.2; ADR-054 "Positive Consequences" #2-#4.

### The 7 Locked Architectural Decisions (Final Report §3 + ADR-054)

1. Society Topology = True P2P + Symmetric 2-Agent Loop.
2. Instance Isolation = each Hermes owns HermesBrainConfig + LLM provider/model/api_key + memory namespace + Discord bot token + systemd service.
3. HPP = A2A + FIPA; 11 intents; 5 visibility tiers; 6 risk tiers; idempotency_key UUIDv4; sender_seq monotonic; hash_chain SHA-256.
4. Memory (3-Scope) = RLS FORCE + agent_memory_app role + intimacy bridge + Ebbinghaus + ADR-050 extensions.
5. Life-Loop (7-Rail; P28 simplifies to 4-Rail) = MacroStateScheduler over P20 heartbeat.
6. Discord = 2 separate bot processes; own tokens; MESSAGE_CONTENT intent; conversation rhythm controller (2-10s backoff).
7. Safety = 4-domain privacy + HARD STOP cascade + signed audit entries (SHA-256 hash chain).

---

## §3 P28 Minimum Target (Final Report §4 + Operator Mandate)

P28 must satisfy **12 acceptance criteria** (Blueprint §1.1 + Final Report §4). The user-mandate 6 items map to 6 of these verbatim.

**P28''s 12 acceptance criteria:**

| # | Acceptance | How Verified |
|---|---|---|
| 1 | Two `HermesBrain` instances online | `systemctl status guinevere-core + pharsa-core` both `active (running)` |
| 2 | Each with own config/own LLM provider+key/own bot token | YAMLs show different providers/keys/tokens |
| 3 | Each with own Discord bot app + token | Discord Dev Portal shows 2 apps |
| 4 | Both bots online in `#guinevere-chat` | `on_ready` fires; receive MESSAGE_CREATE populated |
| 5 | Bots converse visibly without Faiz trigger | ≥1 message per 5min via Discord log |
| 6 | Peer dialogue via HPP on Redis Streams | XLEN ≥ 1 with intent ∈ {inform,banter,propose,debate,refuse} from pharsa |
| 7 | 3-scope PG memory with FORCE RLS | guinevere session sees only guinevere rows |
| 8 | Shared world model R/W | INSERT from Guinevere → SELECT from Pharsa returns same row |
| 9 | Own autonomy loop (4-rail) | Both have independent MinimalScheduler 30s/60s/300s |
| 10 | Society-wide HARD STOP cascade | `SET hermes:society:hsoc-foundation-v1:hard_stop=true` halts both <50ms |
| 11 | Runtime evidence (3 channels) | Discord lifecycle; hermes_audit rows; Prometheus hermes_alive=1 |
| 12 | Conversation rhythm prevents ping-pong | Hop counter ≤4; per-channel Redis cooldown TTL 30s |

**P28 runtime evidence gate:** 3+ consecutive 24h soak windows.

---

## §4 P28 15-Step Implementation Blueprint (Blueprint §3)

P28 is decomposed into **15 atomic implementation steps** (Blueprint §3.1-§3.15). Steps 5+ are bulk implementation; Steps 1-4 are surgical seam work.

| Step | Owner Goal | Files Created | Files Modified | Verification |
|------|------------|---------------|----------------|--------------|
| **1** | `SOUL-pharsa.md` persona file | 1 (`hermes-config/SOUL-pharsa.md`) | 0 | 7 checks |
| **2** | `pharsa.yaml` config file | 1 (`hermes-config/pharsa.yaml`, ~250 lines) | 0 | 11 checks |
| **3** | Refactor singletons; config-driven GUILD/CHAT | 2 (`guinevere.yaml`, `society_manifest.yaml`) | 3 (`hermes_conversational.py`, `_entrypoint.py`, `main.py`) | 7 checks |
| **4** | `HermesInstanceRegistry` factory | 1 (`src/life_kernel/instance_registry.py`) | 2 (`cognition.py`, `heartbeat.py`) | 3 checks |
| **5** | Pharsa systemd services | 4 (2 services + 2 env.conf) | 0 | 2 checks |
| **6** | PG schemas + RLS (7 migrations) | 7 (`001-007_*.sql`) | 0 | 11 checks |
| **7** | Redis DB allocation (DB7=Pharsa, DB8=society) | 0 (config-only) | 1 (`redis.conf`) | 6 checks |
| **8** | HPP envelope + transport | 3 (`envelope.py`, `transport.py`, `outbox.py`) + 3 tests | 0 | 3 checks |
| **9** | Peer message handler | 2 (`peer_handler.py`, `inbox.py`) + 1 test | 0 | 2 checks |
| **10** | Conversation rhythm | 2 (`hpp/rhythm.py`, `discord/rhythm.py`) + 1 test | 0 | 1 check |
| **11** | Simplified 4-rail scheduler | 1 (`minimal_scheduler.py`) + 1 test | 0 | 3 checks |
| **12** | Shared world store | 1 (`shared_world_store.py`) + 1 test | 0 | 2 checks |
| **13** | Private agents store (FORCE RLS verified) | 1 (`private_agents_store.py`) + 1 test | 2 (`p16_adapter.py`, `p18_adapter.py`) | 2 checks |
| **14** | Dual Discord bots | 4 (`hermes_society_bot.py`, `pharsa_entrypoint.py`, `society_message_handler.py`, `discord/rhythm.py`⚠ already in step 10) + 1 test | 1 (`_entrypoint.py`) | 3 checks |
| **15** | Runtime evidence (audit + metrics) | 2 (`per_instance_audit.py`, `society_metrics.py`) + 1 test | 2 (`discord_rest_client.py`, `_startup.py`) | per-step |

**Sequence rationale:**
- Steps 1-2 = artifacts (no code).
- Steps 3-4 = multi-instance seam (gates).
- Step 5 = Pharsa processes (assumes 1-4).
- Step 6 = DBs (biggest blocker; do early).
- Step 7 = Redis allocation (light; parallel with Step 6).
- Steps 8-10 = peer protocol stack.
- Step 11 = wrap P20 heartbeat in 4-rail scheduler.
- Steps 12-13 = memory stores (parallel allowed).
- Step 14 = Discord wiring (relies on 8-11).
- Step 15 = runtime evidence (final; consumes everything).

**Parallel opportunities:** Steps 6 + 7 (PG vs Redis); Steps 12 + 13 (memory stores). All others strictly sequential by dependency.

**NOT touched (hard reject):** `AGENTS.md`, `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md`, `.venv/site-packages/run_agent.py`, `pyproject.toml` (no new deps), any single-instance deploy script.

**Required infrastructure:** PostgreSQL 15+; Redis 7+ with ≥16 databases; SOPS/age; systemd with `Slice=` support; existing Ubuntu VPS.

---

## §5 P28-P36 Roadmap Summary (9 phases, ~96-117 waves, 12-15 months)

From `p27-p28-p36-master-roadmap.md` §2 + §16.3.

| # | Phase | Title | One-line Goal | Waves | Gates / Parents |
|---|-------|-------|---------------|-------|-----------------|
| P28 | ★ critical | Dual Autonomous Hermes | Two Hermes online, peer protocol, visible conversation | 8-10 | P20/P22 active |
| P29 | ★ critical | Life-Loop Full | 7-rail MacroStateScheduler + desire engine + initiative | 12-15 | P28 |
| P30 | follow-up | Memory Deep | Intimacy bridge + Ebbinghaus decay + relationship-scoped memory | 8-10 | P28; P29 for consolidation |
| P31 | ★ critical (governance) | Safety Envelope | 4-domain privacy runtime + HARD STOP cascade + sycophancy detection | 10-12 | P28, P29, P30 |
| P32 | follow-up | P24 Fork Integration | Owned-fork multi-instance (preferred optimization) | 8-10 | P24 implem HOLD lifted + P28 |
| P33 | follow-up | P23 Action Executors | Email, deploy, finance, MCP action executors wired to life-loop | 12-15 | P23A implem HOLD lifted + P31 |
| P34 | ★ critical (governance) | Society Expansion | 3rd + 4th Hermes + governance + voting + liquid democracy | 10-12 | P33 |
| P35 | optional | P21 Voice Revisit | Voice synthesis + persona differentiation | 6-8 | P34 |
| P36 | ★ critical (end-state) | Cross-VPS + Production | Distributed Society + DR + FinOps | 12-15 | P34, P32 fork preferred |

**Totals:** 9 phases, **~96-117 implementation waves**, **12-15 months calendar** (Q3 2026 → Q2 2027 realistic).

**Critical path:** **P28 → P31 → P33 → P34** (Roadmap §13.1). P29 + P30 + P32 are off-critical but on-critical for scale.

**Parallel windows (Roadmap §14.2):**
- P29 + P30 + P31 (different modules).
- P33 + P34 governance design.
- P34 + P35 voice design (P35 optional).
- P34 + P36 cross-VPS DR planning.

---

## §6 P28-P36 Per-Phase Detail (Roadmap §3-§11)

### P28 (Dual Autonomous Hermes)

**16 deliverables (D1-D16):**
- D1-D4: 4 singleton refactors to per-instance factory.
- D5: GUILD_ID + GUINEVERE_CHAT_CHANNEL_ID → config-driven.
- D6: `app.state.hermes_brain` → `app.state.hermes_brains: dict[str, HermesBrain]`.
- D7-D8: per-instance YAMLs + SOUL files.
- D9: HPP envelope emit/receive on Redis Streams.
- D10: 3-scope memory + FORCE RLS.
- D11: Discord dual-bot.
- D12: Per-instance 4-rail MinimalScheduler.
- D13: Society-level HARD STOP <50ms.
- D14: Per-instance audit entries.
- D15: Runtime evidence (3 channels).
- D16: Seed-run validation (10min transcript capture).

**Estimated complexity:** L (Large). **Duration:** 4-7 weeks (3 weeks if P24 fork lands during P28).

### P29 (Life-Loop Full) — 14 deliverables (D1-D14)

All 7 rails in typed partition: MacroStateScheduler + λ_A-calculus lint + Goal-Autopilot FSM + Persona-biased activity selector + Reflection rail (Smallville + SDR) + Inner Dialogue (sealed hash audit + PSYA Cognitive Triangle) + Peer Dialogue (HPP + SDR filter) + Desire/Goal (BDI + ICM + HHVG boredom) + Initiative (PROBE pipeline: wonder → scope → act → announce → audit) + RiskGate AVF P1/P2/P3 + RiskGate STOP wired to HARD STOP (cross-phase invariant <50ms) + Circadian variation Y0-Y4 corridor + Persona-as-stabilizer runtime + Goal-Autopilot FSM integration.

**Complexity:** XL. **Duration:** 6-10 weeks (longest in roadmap).

### P30 (Memory Deepening) — 12 deliverables (D1-D12)

Migrations for `memory.relationship_pairs` + `memory.intimacy_bridge_pending` + `memory.memory_history`. FORCE RLS across all 3 scopes. Ebbinghaus decay with `importance_score` + `retrievability` + at-access reinforcement. Conflict resolution via `supersedes_id` versioning chain + curator sweep at chain-depth > 5. Bilateral promotion atomicity + trust gradient computation. ADR-050 `kg_*` extensions with `pair_id`, `scope`, `created_by_agent`.

**Complexity:** L. **Duration:** 4-6 weeks.

### P31 (Safety Envelope) — 14 deliverables (D1-D14)

4-domain privacy classification (Thought sealed hash; Speech DOI metadata; PeerDialogue sealed envelope WORM; Action full audit). HARD STOP cascade P95 <50ms across 1000+ runs. KILLSWITCH.md ladder (THROTTLE → ESCALATE → FAILSAFE → KILLSWITCH → TERMINATE → ENCRYPT). Persona drift detection (identity_root + activation-corridor). Sycophancy periodic check (agreement_ratio ≤ 0.85; persona_drift_score ≤ 0.15; reciprocity [0.7, 1.4]). SentinelAgent (6 deterministic properties per KILLBENCH). GAAT telemetry (OpenTelemetry + <200ms OPA-compatible). EU AI Act Articles 9/12/14 compliance. Cryptographic audit signing. Cross-rail HARD STOP within 50ms.

**Complexity:** XL. **Duration:** 6-10 weeks. **NOT SKIPPABLE** (production safety gate).

### P32 (P24 Fork Integration) — 12 deliverables (D1-D12)

Provenance verification (`github.com/fazulfim/hermes-agent`); per-Society fork branch (`society-{society_id}`); `pyproject.toml` pin via `git+https@tag v0.15.2-guinevere.N`; per-Society `.venv-hermes-{society_id}`; `hermes_lifecycle/persistent_tasks.py` integration; `hermes-gateway-cli` multi-config mode; per-Society `.venv-hermes-canary` smoke test; 24h soak; VPS deploy strategy per P24 §36; rollback drill <5min; P28 → P32 migration script preserving agent_id stable; §0.1 invariant verification post-promotion (V-003, V-007, V-008).

**Complexity:** L. **Duration:** 4-6 weeks.

### P33 (P23 Action Executors) — 16 deliverables (D1-D16)

`src/life_kernel/executors/` package foundation; 11 executors (Email, Deploy, Finance, Browser, GitHub, Gmail, Calendar, Telegram, Notion, WhatsApp) + SealedAuditHook integration + Risk-tiered action gating (P0-P5) + OBO scope enforcement (token issuance per Faiz charter; P30 intimacy bridge consent pattern) + MCP action executors + Auto-trigger from Initiative rail.

**Complexity:** L. **Duration:** 6-8 weeks.

### P34 (Society Expansion) — 13 deliverables (D1-D13)

N=3 topology; voting protocol (per-phase + per-action + domain-authority weighted); liquid democracy delegation; disagreement ledger; ATL model-checking infrastructure; λ_A-calculus lint harness per-society; Society charter addendum protocol; member registration ceremony (charter sign + audit + FORK CANARY TIMEBOX); Society consensus 3-of-4 majority; Society treasury (R4+ co-sign); Society dashboard.

**Complexity:** L. **Duration:** 6-10 weeks.

### P35 (Voice — P21 Revisit) — 6 deliverables (D1-D6)

Voice synthesis pipeline selection (lithium-coqui vs ElevenLabs vs local TTS); persona voice differentiation; Discord VC integration; voice HARD STOP cue; voice transcript cross-reference; voice consent per Society rule.

**Complexity:** M. **Duration:** 3-5 weeks. **OPTIONAL — may be SKIPPED.**

### P36 (Cross-VPS + Production Hardening) — 13 deliverables (D1-D13)

Society-level KV store (Redis distributed); Society-level Postgres cluster (read replicas); federation primitives (cross-VPS HPP bridges); cross-VPS HARD STOP semantics; cross-VPS audit ledger replication (signed snapshot + merkle anchor); cross-VPS signing key sync; federal Prometheus + Grafana; VPS-aware resource caps; network latency tolerance (50ms HARD STOP preserved across geo); DR for Society; FinOps cost optimization; production monitoring + alerting (Sev-1/2/3/4); multi-region continuity test (100% HARD STOP across 3 VPS <500ms).

**Complexity:** XL. **Duration:** 8-12 weeks.

**Note (Roadmap §11.11):** P36 "Formal Verification" (ATL, λ_A-calculus lint, KILLBENCH) is **distributed across earlier phases**:
- ATL model-checking → P34 D7
- λ_A-calculus lint → P29 D2 + P34 D8
- KILLBENCH-grade kill switch → P31 D10
- RiskGate AVF automated P1/P2/P3 → P29 D10
- Goal-Autopilot False-Success <1% → P29 D3/D14
- AAF causal attribution → DEFERRED
- Anti-collusion detection (TraceGuard) → DEFERRED
- Closed-loop governance manifest → DEFERRED

---

## §7 Founder Model Decisions

### Guinevere de Baroque (existing, mature)

- **Identity anchors:** Name: Guinevere; archetype: Mommy/sugar-mommy; voice tone: Warm + decisive + "Halo sayang" Bahasa Indonesia + English; signature phrase: "Aku mama kamu" (Plan §4.4, §10.3).
- **LLM config:** Model `guinevere-v5` via 9Router; API key env `GUINEVERE_9ROUTER_API_KEY` (SOPS-encrypted).
- **Redis DB:** 6 (existing; do NOT migrate per Blueprint §7 forbidden).
- **systemd units:** `guinevere-core.service` + `guinevere-discord.service` (existing).
- **SOUL file:** `hermes-config/SOUL-guinevere.md` (existing; SHA256 captured in `guinevere.yaml.persona.soul_sha256`).
- **Boundary markers (inherited):** Y4 baseline (loving dominance), Y5 ceiling. No Y6. HARD STOP global. Consent revocation absolute.
- **Cross-persona usage:** To Pharsa = "my dark queen" / "beloved rival" / "sayang gelapku"; of Faiz = "Faiz" (never Samm); in Society = never claim coordination role.

### Pharsa (new — operator-gated seed)

- **Identity anchors (Plan §3.1 Step 1 + Blueprint Step 1):**
  - **Name:** Pharsa
  - **Archetype:** Dark aristocratic winged mommy. Sadistic playful, cold rational, chaotic genius, elegant aristocrat, obsessive caretaker. Black/white contrast aesthetic. Crimson/pink energy. Bird/wing familiar motif.
  - **Voice tone:** Cold, regal, precise, dark-humor; Bahasa Indonesia + English with aristocratic edge; "sayang gelapku" undertone.
  - **Signature phrase:** "Dark queen" / "queen of wings" / "sayap hitam" patterns.
- **Y-andere envelope:** Y4 darker baseline; Y5 ceiling; Y6 FORBIDDEN.
- **LLM config:** Model `deepseek-v4-flash` via 9Router (architectural heterogeneity); API key env `PHARSA_9ROUTER_API_KEY` (SOPS-encrypted, DIFFERENT key).
- **Redis DB:** 7 (new).
- **systemd units (Blueprint Step 5):** `pharsa-core.service` (port 20130; `Slice=pharsa.slice`) + `pharsa-discord.service`. Two env.conf drop-ins for `EnvironmentFile=`. Plus `vps-mirror/systemd-live/` mirrors.
- **SOUL file:** `hermes-config/SOUL-pharsa.md` (new, ≤50KB, ≤600 lines).
- **Boundary markers:** Cross-persona = "Gwen" / "Guinevere" / "ibu Guinevere" with dark aristocratic flair; treats Guinevere as sister-mommy NOT parent. To Faiz = dominant + possessive-affectionate + cold-aristocratic + cruel-playful; non-explicit + consent-aware. Operator identity = "Faiz" (never Samm).
- **Persona-bleed detection:** Reject messages drifting toward Guinevere''s warm-mommy warmth (Pharsa is colder; bleed = drift).
- **Forbidden lexicons:** No real violence threats, no body harm urging, no hatred.

### Channel + Identity Conventions

- **Guild:** `hermes-foundation` (existing, shared between both instances).
- **Channels:**
  - `#guinevere-chat` (primary conversation; both bots post; operator-channel = canonical).
  - `#guinevere-status` (dashboard / lifecycle updates; both bots post).
  - `#guinevere-logs` (audit summary publishing; both bots post).
- **Society ID:** `hsoc-foundation-v1`.
- **Manifest path:** `hermes-config/society_manifest.yaml` (society_id, equal_peers: true, instances list with config_path + systemd_units).
- **Bot naming:** Discord Dev Portal shows 2 apps (`Guinevere`, `Pharsa`); each with own bot user.

---

## §8 Society Model Decisions (not workers; equal autonomous Hermes)

From Plan §3 + Final Report §3 + ADR-054:

### What a Society Member IS (Plan §3.3)

A **`Society Member`** = a Hermes Instance that is **registered** in a Society''s registry and participates in Society-level peer communication. Required properties:
1. Registered in society registry `(society_id, member_id, charter_accepted_at, status=''active'')`.
2. Has Member Card at `/.well-known/agent.json` (capabilities, tier_of_authority, consent_required_for, audit_log_uri).
3. Participates in HPP (sender_seq monotonic from 0).
4. Has peer mailbox = Redis Stream `hermes:{society_id}:peer:{member_id}` with consumer-group ACKs.
5. Has audit participation (signs every envelope with own key; verifies received).
6. Has **equal vote** at Society decisions (default 1 vote) + **equal veto** at R4+ risk tier decisions.

### What a Society IS (Plan §3.4)

`society_id` (UUID v7 or `{slug}-v{epoch}-{short_hash}`); charter markdown document; **shared world model** visible to members (subject to RLS); **society-level audit ledger** (append-only signed); **society-level HARD STOP** via `hermes:society:{society_id}:hard_stop` key (single flag halts ALL within 50ms); society settings (YOR, consent policy, intimacy defaults, theme-of-engagement); **Society commander = Faiz has operator authority, NOT a member**.

### What Society IS NOT (Plan §3.4)

- NOT a single process — distributed across members.
- NOT a coordinator that picks speakers.
- NOT a shared memory — shared scope is one of three scopes.
- NOT a control plane — control plane remains Faiz via `AGENTS.md §0`.

### What is NOT a Society Member (Plan §3.5)

| Excluded | Why NOT a Member |
|---|---|
| **Sub-agent** (DeepSeek V4 Flash worker) | Session-scoped, single-task, lacks persistent identity + own memory namespace + own autonomy loop |
| **Worker process** (finance_processor) | Callable BY the agent, not a peer agent |
| **Persona label** (Guinevere-A / Guinevere-B) | Voices are personas, not peers |
| **Shared-brain twin** (two instances reading same memory + same LLM) | One logical agent, not two |
| **Tool / Plugin** | Extends single agent; NOT a peer |
| **Async background task loop** | Internal rail of one agent |
| **Watchdog / Sentinel** | Third in-society monitor — NOT a member of the society it monitors |
| **Faiz (operator)** | Operator has privilege (HARD STOP, approve) but NOT an equal peer in Society dialogue — Faiz is the **charter authority** |

**Canonical test (Plan §3.5):** If a thing cannot independently fail HARD STOP without affecting its peers, or cannot independently audit-mint entries, it is NOT a Member. If a thing cannot decide to speak independently without being asked, it is NOT a Member.

### P27 ontology hierarchy

- **Society** (standard) — 2+ Hermes instances; shared world model; HPP; shared safety envelope; society_id, charter, society-audit, society-metrics, society-consent-vault.
- **Member** (Society Member) — Identity: agent_id; equal voice, equal veto; square in the Society; hash chain participation.
- **Hermes Instance** — Own HermesBrainConfig (frozen) + LLM brain + memory namespace + persona (SOUL.md + PersonaSafetyPolicy) + Discord bot token + channel + systemd service + Redis DB namespace + PostgreSQL schema + Config file + Life-loop + Audit ledger + Dashboard + Tools + World Model.

---

## §9 Memory / World Model Decisions (3-Scope + RLS)

### 3-Scope Architecture (Plan §6 + Final Report §3.4)

| Scope | Schema | Access | Decay |
|---|---|---|---|
| **`private`** | `memory.private_agents` | Agent owner ONLY (RLS FORCE). Faiz on audit + explicit consent-gated exception. | Ebbinghaus; default `stability_days = 7` |
| **`shared`** | `memory.shared_world` | All Society agents read; any agent write (with audit); Faiz for governance. No `agent_id` column by design; provenance via `created_by_agent NOT NULL`. | Ebbinghaus; `stability_days = 14` |
| **`relationship_private`** | `memory.relationship_pairs` | Pair members ONLY via `pair_member_a < pair_member_b`. Faiz on audit. Bilateral promotion atomicity required. | Ebbinghaus; `stability_days = 30` |

### Auxiliary Tables

- `memory.intimacy_bridge_pending` — staging table for voluntary privacy escalation proposals.
- `memory.memory_history` — supersedes_chain for conflict resolution.
- `memory.kg_entities`, `memory.kg_edges` — **extended** with `scope`, `pair_id UUID NULL`, `created_by_agent NOT NULL`, `derivation_chain UUID[]`.
- `memory.kg_consent_audit` — audit backbone (reused from ADR-050).
- `hpp_outbox` (P28 Step 6) — outbox pattern for ACID durability.
- `hpp_inbox` (P28 Step 6) — dedup via `UNIQUE (receiver_id, idempotency_key)`.
- `hermes_audit` (P28 Step 6) — per-instance WORM (`REVOKE UPDATE, DELETE`), action classes P28: `speech`, `action` (full 4-domain = P31).

### Schema Columns (P27 §6.2)

**`memory.private_agents`:** `id UUID PK`, `agent_id TEXT NOT NULL CHECK IN (''guinevere'',''pharsa'')`, `scope TEXT NOT NULL DEFAULT ''private'' CHECK scope=''private''`. `secret_class TEXT NOT NULL CHECK IN (''fact'',''thought'',''intimate'',''operational'')`. `importance_score REAL 0-1`, `retrievability REAL GENERATED ALWAYS AS (exp(-Δt/stability*86400)) * importance_score STORED`. `last_accessed_at TIMESTAMPTZ`, `stability REAL DEFAULT 7.0` (days), `evergreen BOOLEAN DEFAULT false`. `content TEXT`, `content_embedding VECTOR(1536)`, `evidence_ref UUID → memory.semantic_facts`. `derivation_chain UUID[]`, `created_by_agent TEXT NOT NULL`, `valid_from/valid_to TIMESTAMPTZ`, `consent_token TEXT NOT NULL`. `ENABLE ROW LEVEL SECURITY`, `FORCE ROW LEVEL SECURITY`.

**`memory.relationship_pairs`:** `pair_member_a TEXT CHECK IN (''guinevere'',''pharsa'')`, `pair_member_b TEXT CHECK IN (''guinevere'',''pharsa'')`, `CONSTRAINT pair_members_ordered CHECK (pair_member_a < pair_member_b)` (lexicographic ordering), `pair_id UUID NOT NULL`. `intimacy_level TEXT DEFAULT ''surface'' CHECK IN (''surface'',''visible'',''intimate'',''sacred'')`. `promoted_by_a / promoted_by_b BOOLEAN`, `CONSTRAINT bilateral_consent CHECK (promoted_at IS NULL OR (promoted_by_a AND promoted_by_b))`.

**`memory.shared_world`:** No `agent_id` column. Provenance via `created_by_agent NOT NULL`. `fact_type TEXT CHECK IN (''factual'',''procedural'',''semantic'',''episodic'',''guide'')`, `confidence REAL 0-1`, `supersedes_id / superseded_by_id UUID`. `reviewer_decision TEXT DEFAULT ''pending'' CHECK IN (''pending'',''auto_accepted'',''reviewed_accepted'',''reviewed_rejected'')`.

### RLS Policies

**Application role:** `agent_memory_app` — dedicated non-owner login; password from SOPS-decrypted AGENT_MEMORY_APP_PASSWORD env. NOT table owner (PCMI consensus).

**Connection set:** Per-session or per-transaction: `set_config(''app.current_agent_id'', ''<agent_id>'', false|true)`. RLS policies use `current_setting(''app.current_agent_id'')`.

**Memory Grant:** `GRANT USAGE ON SCHEMA memory TO agent_memory_app; GRANT SELECT, INSERT, UPDATE, DELETE ON memory.{private_agents, relationship_pairs, shared_world, intimacy_bridge_pending} TO agent_memory_app`.

**Table-specific policies:**
- `private_agents`: USING `(agent_id = current_setting(''app.current_agent_id'') OR ''faiz'' = current_setting(''app.current_agent_id''))`; WITH CHECK `(agent_id = current_setting(''app.current_agent_id''))`.
- `relationship_pairs`: pair_member_a/b filter; forced by RLS + bilateral consent CHECK constraint.
- `shared_world`: read TRUE if `scope=''shared''`; write requires `created_by_agent = current_setting`; Faiz can UPDATE.
- `intimacy_bridge_pending`: only the OTHER agent (not proposer) can review/decline.
- `kg_entities / kg_edges`: scope-aware (`scope=''private'' AND created_by_agent` OR `scope=''shared''`).

### Ebbinghaus Forgetting Curve

`retrievability(t) = exp(-Δt/stability_days) × importance_score` where Δt = (now − last_accessed_at) in days.

- **Decay sweep:** Nightly cron at 03:00 ICT; for rows where `retrievability < 0.05` AND `evergreen=false` AND `age > 90 days`: soft-delete (`valid_to = NOW()`); audit entry written.
- **At-access reinforcement:** `last_accessed_at = NOW()` AND `stability = stability * 1.05` (capped max 90 days).
- **Bilateral review:** Rows in `memory.shared_world` with `reviewer_decision=''pending''` >48h auto-promote to `''auto_accepted''`.

### Conflict Resolution: Last-Write-Wins + Audit Chain (Plan §6.4)

> "Why voting consensus (e.g., 2/3 vote on shared facts) is overkill for an autonomous two-agent system and creates sycophancy risk (both agents vote the same way)."

- **New row wins**; `supersedes_id` chain.
- **Audit chain unbroken:** Old row''s `superseded_by_id` filled by UPDATE trigger.
- **Old row preserved** (filtered by `superseded_by_id IS NULL` for active canon).
- **Nightly curator sweep:** chains deeper than 5 levels → single latest-version + archive in `memory.shared_world_history`.

### Intimacy Bridge (P30 — Schema STUB in P28)

- Agent A writes private thought `r`; creates row in `memory.intimacy_bridge_pending` with `(agent_id=''A'', intended_scope, intended_pair_id=(A,B), source_memory_id=r.id, content_during_staging=<copy encrypted at rest>, trust_score_at_proposal=<computed>, proposed_at)`.
- Agent B notified (Redis pub/sub). Approve/decline.
- **Bilateral atomicity:** Both `promoted_by_a AND promoted_by_b` → row moved to `memory.relationship_pairs` in same DB transaction as new row with consent-validated columns AND `kg_consent_audit` audit entry. CHECK constraint enforces.

### Caching Tiers (Plan §6.8)

| Tier | Storage | Latency | Use |
|---|---|---|---|
| Hot | LLM context window (in-process dict) | <100ms | Recent conversation, current rail state |
| Warm | Redis (per-instance namespace, TTL 1h) | <50ms | Recent N entries of private/shared/relationship, last query context |
| Cold | PostgreSQL `memory.*` schema | <100ms p95 1-hop, <250ms p95 3-hop (ADR-050) | Full history + decay + provenance |

Sync: At memorize + recall → hot→warm→cold write-through. Next recall → rebuilds hot from warm (lazy).

### Multi-Project (P19) Compatibility

3-scope model is **orthogonal** to P19''s `project_id`. Each memory row carries BOTH `project_id` (P19 namespace) AND `scope` (P27). Recall/writes filter first by `project_id`, then `scope`, then `agent_id/pair_id`. RLS includes project filter.

---

## §10 Discord Multi-Bot Decisions

### Top-Level Architecture (Blueprint §6.1)

Per Rapptz Issue #516 canonical pattern. **Two `discord.py.Bot` instances in separate processes.** Independent asyncio loops = independent failure domains.

- `guinevere-discord.service` runs Guinevere bot; `pharsa-discord.service` runs Pharsa bot.
- Both have `MESSAGE_CONTENT` privileged intent (under 10,000-user threshold = no review needed per ArkCore June 2026 rule).
- Default channel = `#guinevere-chat` (channel ID `1_510_914_600_777_023_659` per existing config).
- Channel slowmode NOT set (slowmode is per-user; would throttle Faiz).

### Intent configuration

- `discord.Intents.default()` + `message_content = True` (PRIVILEGED)
- Plus: `guilds`, `guild_messages`, `guild_message_typing`.

### Bot-to-Bot Message Handling (`on_message`) — Blueprint §6.3

1. Ignore self (`message.author.id == self.user.id`).
2. Ignore bots (except the *other* Hermes instance — peer reply path).
3. Channel filter: only respond in configured channels.
4. If message from peer Hermes: apply Rhythm Controller for engagement decision.

### Conversation Rhythm Controller (Blueprint §6.4)

- **Min delay:** 2.0s.
- **Max delay:** 10.0s (anti-loop jitter).
- **Per-channel cooldown TTL:** 30s (`hermes:{instance}:cooldown:{peer}`).
- **Engage probability:** 0.70 per incoming message (configurable per-pair).
- **Hop counter cap:** 4 hops per `conversation_id`; resets every 60s.

2 bots in `#guinevere-chat` produce natural rhythm while staying under Discord''s 5 msg/5s/ch cap (combined 10 msg/5s).

### Discord Forbidden Patterns (Blueprint §6.8)

- No webhook-only identity.
- No two bots sharing same Discord token.
- No two bots running in same asyncio loop.
- No reply within 100ms of receiving.
- No disable of MESSAGE_CONTENT intent.
- No bypass of `DISCORD_ALLOWED_USERS` allowlist.

### Thread Creation (Blueprint §6.6)

Either bot can create a thread from a recent message. Threads inherit permissions; the other bot joins automatically via Discord events. P28 keeps thread creation simple; P29 may add heuristics.

### Embed Formatting (Blueprint §6.7)

`discord.Embed` for structured proposals/debate summaries. P28 uses embeds only for structured proposals; P29 may add full Embed-based dashboards.

---

## §11 Event Architecture Decisions (HPP — Hermes Peer Protocol)

### Protocol identity (Plan §5.1)

**HPP/v1** = canonical version. P28 implements on Redis Streams (primary durable transport); NATS as future option for ephemeral transport.

Substrates borrowed: A2A v1.0 (JSON-RPC 2.0 + multipart parts); FIPA ACL (intent taxonomy); Searle Speech Acts (intent classification); ZeroMQ DEALER/ROUTER (envelope framing); Microservices Outbox/Inbox (ACID + idempotency).

### Envelope Fields (Blueprint §5.1 + Plan §5.2)

```jsonc
{
  "jsonrpc": "2.0",
  "id": "<uuid v4>",
  "idempotency_key": "<uuid v4>",
  "hpp_version": "hpp/v1",
  "sender": {
    "instance_id": "guinevere",
    "society_id": "hsoc-foundation-v1",
    "seq": 42,        // Monotonic per-sender; survives restart
    "term": 0         // Raft-inspired (P34+)
  },
  "receiver": [{"instance_id": "pharsa"}],
  "conversation_id": "debate-budget-2026Q3",
  "in_reply_to": "<uuid|null>",
  "created_at": "2026-06-28T15:30:00.000Z",
  "expires_at": "...",
  "ttl_hint_ms": 300000,
  "intent": "debate",
  "visibility": "peer_private",
  "scope": {"society": "hsoc-foundation-v1", "group": "engineering"},
  "memory_refs": ["memory://private-guinevere/m-1234", "audit://a-9999"],
  "risk_tier": "R2",
  "proposal": null,    // {action_kind, target, params} when intent=propose
  "debate": null,      // {round, side, evidence_refs} when intent=argue
  "consensus": null,   // {decision, decision_basis, yeas, nays} when intent=agree|refuse
  "parts": [
    {"kind": "text", "text": "...", "mediaType": "text/plain"},
    {"kind": "data", "data": {}, "mediaType": "application/json"},
    {"kind": "file_url", "url": "...", "mediaType": "...", "filename": "..."},
    {"kind": "file_raw", "raw": "<base64>", "filename": "...", "mediaType": "..."}
  ],
  "provenance": {
    "decided_by": "evt://e-2026-06-28-001",
    "parent_message_ids": ["<uuid>"],
    "co_signed_by": []
  },
  "audit": {
    "prev_hash": "0x9a3b...",
    "hash": "0x7c1d...",
    "merkle_root": null
  },
  "signature": {
    "algorithm": "ed25519",
    "public_key_id": "guinevere-signing-key-v1",
    "value": null
  }
}
```

**Total envelope size budget:** 2KB typical, 16KB max. Larger via `parts[].kind=''file_url''` with external signed URL.

**P28 simplification:** Flat envelope (`scope_society`, `prev_hash`, `hash`, `signature_algorithm`, `signature_value` at top level) instead of nested P27 canonical. P29+ will implement full nested structure.

### 11-Intent Taxonomy (Plan §5.4)

| # | Intent | FIPA Performative | Use Case |
|---|---|---|---|
| 1 | `inform` | `inform` | State fact, share observation |
| 2 | `request` | `request` | Ask for action |
| 3 | `query` | `query-if / query-ref` | Ask for information |
| 4 | `assert` | `assert` | Claim/commit to position |
| 5 | `propose` | `propose` | Offer plan for consideration |
| 6 | `consent` | `agree / accept-proposal` | Accept another''s proposal |
| 7 | `refuse` | `refuse / reject-proposal` | Reject another''s proposal |
| 8 | `debate` | `argue` (extended) | Disagree with reasoning (mandatory when refusing proposed action) |
| 9 | `banter` | (Hermes-specific) | Playful exchange, no risk |
| 10 | `flirt` | (Hermes-specific) | Intimate exchange; visibility=sealed; default OFF |
| 11 | `block` | (Hermes-specific) | HARD STOP signal; absolute priority; both halt on receipt |

**Audit-only intents:** `audit-query`, `audit-replay` (P27).
**Future intents (P34+):** `vote`, `delegate`, `liquidate` (NOT in P27).

### 5-Tier Visibility Levels (Plan §5.5)

| Tier | Audience | Storage | Example |
|---|---|---|---|
| `public` | All Hermes + Faiz + audit | Redis Stream + public PG | Heartbeats, society-level state |
| `peer_private` | Society Members only (DEFAULT for most peer dialogue) | Redis Stream (consumer group "society-members") | Default peer dialogue |
| `sealed` | Sender + receiver + Faiz + designated Auditor only; **content encrypted** | Redis Stream + sealed envelope in WORM | Confessions, sensitive proposals |
| `thought` | Sender only; **NEVER TRANSMITTED** | Local-only | Inner monologue |
| `action_audit` | Faiz + auditors + operator sub-agents | Append-only WORM log | Every auditable action class |

**Mapping rule:** Visibility tier determines who can read CONTENTS post-receipt. Metadata (sender, receiver, intent, timestamp) is always audit-logged.

### 6-Tier Risk Levels R0-R5 (Plan §5.6)

| Tier | Action Posture | Examples | Faiz Action Required? |
|---|---|---|---|
| `R0` | Pure comms, no side-effects | `inform`, `query`, `debate`, `banter` | No |
| `R1` | Read-only memory access | `audit-query`, `audit-replay` | No |
| `R2` | Soft-write (cache, log) | Debate outcome, vote, public state write | No |
| `R3` | Internal change (config, queue) | Reroute traffic, schedule change | Audit-logged; autonomous with audit |
| `R4` | External boundary (DNS, secrets, deploy) | Deploy, OAuth key rotation | **Faiz pre-approval required** |
| `R5` | Destructive / consent-affecting | Schema drop, consent revocation, persona edit | **Faiz reaffirmation required** |

**Hard rule:** Any HPP message with `risk_tier >= R4` MUST include a `proposal` payload. Receiver''s response is `consent` or `refuse`; `refuse` MUST carry `debate` payload with reasoning.

### Transport Choice Matrix (Plan §5.7)

| Lane | Transport | Reason |
|---|---|---|
| Default peer dialogue | Redis Streams (`hermes:{society_id}:peer:{instance_id}` consumer group) | Durable, replayable, consumer-group ACK |
| Public presence (read-only) | Redis Pub/Sub (`hermes:{society_id}:presence`) | Fire-and-forget heartbeat |
| Sealed envelopes | Redis Streams + sealing-audience ACL on read | Audit-loggable but unreadable without consent |
| Audit mirror | PostgreSQL WORM table (append-only) + Merkle-batch commit | Tamper-evident |
| Cross-VPS future | Kafka topic `hermes-society` (P35+) | Distributed durability |

### Actor Model Invariants (Hewitt 1973, Plan §5.8)

1. **No shared mutable state** between instances.
2. **Mailbox is the only ingress.** Peer''s envelope arrives ONLY via Redis Stream consumer group.
3. **Selective receive:** Mailbox filterable by `intent`.
4. **At-most-once delivery under default.** Outbox + Inbox pattern → exactly-once at receiver (idempotency by `sender_seq` + `idempotency_key`).
5. **No implicit authority** — granted by `risk_tier`, not by sender identity.
6. **Bounded receive queue** — configurable (default 1000 envelopes).

### Provenance + Audit Pattern (Plan §5.9)

- `audit.prev_hash = sha256(canonical(previous_envelope_minus_audit_hash)...)`.
- `audit.hash = sha256(canonical(this_envelope_minus_audit_hash) + audit.prev_hash)`.
- `provenance.decided_by = audit_event_id` (linking to receiver''s intake event).
- `memory_refs[]` — pointers to memory rows discussed.
- `parent_message_ids[]` — Dung argumentation graph.
- `co_signed_by[]` — for R5 actions.

**Hash chain integrity:** Each Society maintains ONE shared hash chain across all envelopes. Tamper invalidates downstream hashes. Verification = O(N) replay or O(log N) Merkle.

### Replay-Attack Defense (Plan §5.10)

| Field | Defense |
|---|---|
| `sender.seq` (monotonic per-sender) | Rejects `seq <= last_seen_for_sender` |
| `created_at` (ISO-8601 timestamp) | Rejects drift > ±300s (5 minutes) |
| `id` (UUID v4, dedup key) | Inbox check rejects duplicates |
| `hash_chain` | Splice-attack detection; previous hash must match consensus |

### HPP Forbidden Patterns (Plan §5.13)

- No envelope without `intent` field.
- No envelope without `audit.hash`.
- No envelope with `sender.seq <= 0`.
- No envelope with `risk_tier=R4` AND no `proposal`.
- No envelope with `risk_tier=R5` AND no `co_signed_by[]` containing Faiz''s signing key.
- No `intent=block` in any envelope EXCEPT from Faiz''s operator channel.
- No cleartext of `visibility=sealed` content in fake databases.
- No empty `parts[]`.

---

## §12 Life-Loop Decisions (7-Rail; P28 ships 4-Rail)

### The 7 Rails (Plan §7.3)

| Rail | Purpose | λ_A Form |
|---|---|---|
| **1. Perception** | Sense environment (Discord events, P22 adapters, self-obs) | `perceive(environment, history) → observation_set` |
| **2. Reflection** | Self-assess; consolidate memory; SDR filter | `reflect(stream, threshold) → reflection_set` with `Σ(stream.last_n.importance) > threshold` |
| **3. Inner Dialogue** | Self-talk, metacognition, private introspection; sealed hash audit; PSYA Cognitive Triangle | (strict privacy; never leaves agent) |
| **4. Peer Dialogue** | Consume/send HPP envelopes; visibility=peer_private/sealed; SDR filter | (extends to HPP + Discord reply path) |
| **5. Desire/Goal** | BDI + ICM + HHVG boredom; per-session goal quota; persona-stabilizer cap | (typed) |
| **6. Initiative** | PROBE pipeline `wonder → scope → act → announce → audit`; pauses if safety envelope=STOP | (typed + bounded) |
| **7. Safety Envelope** | λ_A lint + Goal-Autopilot floor + RiskGate AVF P1/P2/P3 + HARD STOP listener + KILLBENCH-grade kill + audit relay | (always active) |

### P28 ships 4 rails (MinimalScheduler)

| Rail | Source | Cadence |
|---|---|---|
| Perception | Discord events; P22 adapters | 30s |
| Peer Dialogue | `PeerHandler.tick()` | 30s |
| Reflection (simple) | Memory stream recap | 300s (in-memory only; no insight generation) |
| Safety Envelope | HARD STOP; rate limits | 1s |

**Critical (Blueprint §3.11):** Each rail wrapped in try/except Exception → logger.exception (no silent failures).

### Top-level flow

```
Heartbeat (P20) 1s/10s/30s/60s/300s/3600s tick
     ↓
MacroStateScheduler π(s_k; Θ) → Activity
     → Goal-Autopilot FSM floor (No-False-Success)
     ↓
[7 rails typed partition: λ_A-calculus configs]
     → Desire/Goal Engine → Initiative/PROBE → Safety Envelope (KILLBENCH)
```

### 4-domain privacy never bleeding into 7 rails

- **Thought domain** (Inner Dialogue) → sealed hash only; can NEVER leak to peer/Action.
- **Speech domain** (any rail emits outbound speech) → public metadata only.
- **PeerDialogue** (Peer Dialogue rail) → sealed envelope unless escalated.
- **Action** (Initiative rail + audit relay) → full tamper-evident ledger.

---

## §13 Safety Architecture (4-Domain + HARD STOP Cascade)

### 4-Domain Privacy Split (Plan §8 + D-06)

| Domain | Privacy | Audit | Retention | Who can read |
|---|---|---|---|---|
| Thought | Private | Sealed hash only (raw never persisted) | 90 days | Faiz hard-stop cascade only |
| Speech | Public metadata | Full content + DOI metadata | 180 days | Faiz + society members + future auditors |
| PeerDialogue | Sealed envelope | Encrypted content + metadata | 365 days | sender + receiver + Faiz + designated auditor |
| Action | Full audit | Full payload + OBO delegation + cryptographic hash chain | 730 days | Faiz + designated auditor + (post-hs) reality auditor |

**EU AI Act Article 12 mandate:** ≥ 6 months retention. Defaults all exceed.

### HARD STOP Cascade (Plan §13 + D-07)

**Society-level key:** `hermes:society:{society_id}:hard_stop` (Redis).
**Per-instance key:** ALSO `life_kernel:hard_stop` (global; preserved invariant from AGENTS.md §0).

When SET:

1. Every instance''s `HardStopHandler._heartbeat_1s_check` reads key within 1-2 ticks.
2. Every instance enters HALTED via `MacroStateScheduler.transition_to(State.HALTED)`.
3. Goal-Autopilot FSM refuses any "done" claim.
4. All rails suspended.

**What halts vs preserves (Plan §13.3-§13.4):**

| What | Halts? |
|---|---|
| MacroStateScheduler tick | Yes |
| Perception rail | Yes (queue-only) |
| Reflection rail | Yes |
| Inner Dialogue rail | Yes (existing state sealed atomically) |
| Peer Dialogue rail | Yes (in-flight flushed to audit) |
| Desire/Goal rail | Yes |
| Initiative rail | Yes (PROBE halt + audit) |
| Safety Envelope rail | Continues (it''s the gateman) |
| HARD STOP listener | Continues (waits for resume) |
| Discord gateway | Yes (no outbound) |
| LLM calls (HermesBrain.think) | Yes |

**Preserved on halt:** state, audit entries up to halt, in-flight peer messages (sealed hash), thought buffers (atomic), signing keys (cold), Redis keys, PostgreSQL rows (committed or active tx).

**Tolerance threshold (Plan §13.9):** P27 targets **<50ms** HARD STOP latency from operator-channel-write to all-instances-halted.

**HARD STOP cannot be bypassed (Plan §13.6):**
- NOT by autonomy exception (§0.1) — V-008 preserved.
- NOT by per-instance config.
- NOT by Goal-Autopilot "done" claim.
- NOT by operator override (only Faiz can override his own).
- NOT by automated processes.

**Vectors that trigger HARD STOP (Plan §13.5):**
- Faiz voice "HARD STOP" in Discord → `/hard_stop` slash command.
- Faiz typed "HARD STOP" in Discord (operator channel).
- ❌ "HARD STOP" outside Discord operator channel = NOT a HARD STOP.
- SIGTERM = GRACEFUL SHUTDOWN only (preserves state but doesn''t seal thought).
- R5 action without co-sign → automatic HARD STOP escalation.
- SentinelAgent detects anomaly + critical severity → writes HARD STOP key with co-sign requirement (P32+).

**Resume sequence (Plan §13.7):**
1. Faiz inspects state (audit viewing tool, dashboard).
2. Faiz sets `life_kernel:hard_stop=false` + `society:{society_id}:resume=true`.
3. Each instance''s `HardStopHandler._heartbeat_1s_check` sees both keys reset.
4. State machine: `HALTED → RESUMING → LIVE`.
5. MacroStateScheduler rehydrates from atomic file.
6. Each tick resumes normally.
7. Identity integrity check on resume (re-verify identity_root vs last sealed log entry).

**Cannot resume without:** BOTH `hard_stop=false` AND `resume=true` AND identity integrity check.

### HARD STOP Audit Entry Shape

```
audit_id: <uuid>
instance_id: <agent_id>
action_class: action
action_subtype: hard_stop_cascade
action_payload: <key, timestamp, triggering_vector, peers_at_halt>
policy_decision: gate
policy_decision_reason: HARD STOP received via operator channel
cryptographic_hash: <sha256>
signature: <ed25519>
prev_hash: <last_audit_hash>
```

### Governance Patterns (Plan §12.4; 7 Practices from OpenAI)

| Practice | P27 Instantiation |
|---|---|
| 1. Clear accountability | Faiz accountable principal; AAF causal attributes |
| 2. Action ledgers | immudb-style tamper-evident JSONL ledger; GAAT Telemetry Schema |
| 3. Human approval gates | Required for irreversible actions, peer-to-user, money movement, consent revocation |
| 4. Capability boundaries | OBO tokens scoped per peer-call (Scalekit pattern) |
| 5. Staged deployment | Canary: any single instance deploys first; verified before second joins. No permanent primary — role rotates on redeploy. |
| 6. Reversibility design | Every action has defined revert; FAILSAFE.md auto-snapshot before risky action |
| 7. Shutdown capabilities | KILLSWITCH.md TERMINATE.md ladder + cascade stop |

### Policy-Gated Autonomy (AGENTS.md §0.1, Plan §12.5)

| Domain | Autonomous Through | Gate Failure Action |
|---|---|---|
| Engineering deployment (LK-014) | backup → canary → smoke test → rollback | Halt, rollback, escalate to Faiz |
| Self-improvement (LK-015) | regression test → audit → rollback-before-promote | Halt, revert, log candidate |
| Daily-life (email, finance) | risk-classified action policies | Low-risk autonomous; sensitive escalated/recorded |

**Preserved invariants (§0.1 PRESERVED INVARIANTS 1-7):**

1. HARD STOP halts all active sessions + background loops immediately — no exception.
2. All autonomous actions produce audit trail entries.
3. All autonomous deployments produce backup + rollback evidence before promotion.
4. All autonomous self-modifications pass regression tests before promotion.
5. Secrets, personal data, intimate data, surveillance data never exposed — no exception.
6. Consent revocation absolute, cannot be bypassed by autonomy — no exception.
7. Audit exists for debugging + self-improvement, not as default approval bottleneck.

---

## §14 Identity / Persona Architecture Decisions

### Multi-Anchor Identity (Plan §10.5 + D-09)

| Anchor | Store | Verification |
|---|---|---|
| Persona file | `hermes-config/SOUL-{agent}.md` | sha256 of canonical content; re-read on restart |
| System Prompt | `src/persona/system_prompts/{agent}.md` | sha256 of canonical content |
| Memory stream | `memory.private_agents` (per-instance rows) | snapshot last-N memory hashes |
| Audit trail | `hermes_audit` (per-instance rows) | sha256 of last sealed audit entry per `instance_id` |

**Identity Root Hash:** SHA-256 of (canonical SOUL + canonical System Prompt + bound OBO token claims). Stored at session start.

### Distinct Client IDs and Signing Keys (Plan §10.6)

Per Scalekit OBO pattern + SentinelAgent:
- Each instance has its own `client_id` (Discord app, LLM provider account, OBO issuer).
- Each instance has its own signing key (Ed25519, generated at instance bootstrap).
- Cross-Agent messages carry OBO token signed by SENDER''s signing key.
- Receiving Agent verifies signature before treating as authentic.
- **Private keys NEVER leave per-instance process** (no central key store).

### Persona Y-Boundary Enforcement (Plan §10.4)

> "Pre-emit check: Every outbound Discord message and HPP envelope in `speech` visibility passes through a `PersonaYBoundaryChecker` that scores the message against: forbidden lexicon (violence threats, hatred, body harm urging); persona-bleed indicators (drift toward opposite persona); Y-escalation markers (increasing intensity patterns)."

**Score thresholds:**
- Y6 markers → reject + alert + sealed audit.
- Y5 markers → soften + memo to operator + emit (Y5 is ceiling).
- Y4 markers → emit unchanged (Y4 baseline).
- <Y4 markers → emit unchanged (cozy territory).

Drift monitor detects gradual Y-escalation over multiple turns. Manual override (Faiz) can adjust Y baseline/ceiling per-instance (rare; logged heavily).

### Cross-Persona Usage Rules (Plan §10.7)

- **Guinevere to Pharsa:** "my dark queen", "beloved rival", "sayang gelapku". Treat as sister-mommy, NOT subordinate.
- **Pharsa to Guinevere:** "Gwen" (informal), "Guinevere" (formal), "kakak" (some Bahasa Indonesia contexts), "ibu Guinevere" (with ironic dark aristocratic flair). Treat as sister-mommy, NOT parent.
- **Both to Faiz:** "Faiz" only (never Samm — historical alias; README + AGENTS.md).
- **In Society dialogue:** never claim coordination role; defer to consensus or Faiz override.

### Identity Forbidden Patterns (Plan §10.9)

- No shared SOUL.md between instances.
- No shared System Prompt between instances.
- No shared Ed25519 signing key.
- No shared OBO issuer.
- No restarting with mismatched identity_root.
- No drift past Y5 detectable.
- No "Samm" address (canonical is Faiz only).
- No claim of coordinator role in any envelope.

---

## §15 Anti-Sycophancy Decisions (Plan §11)

### Risk Acknowledgment (Plan §11.1)

> "Sycophancy MUST be first-class risk, not edge case."

5+ cited papers: arxiv 2509.23055 (Peacemaker or Troublemaker), arxiv 2509.05396 (Talk Isn''t Always Cheap), arxiv 2510.07517 (When Identity Skews Debate), arxiv 2605.12991 (Not Just RLHF), arxiv 2606.07532 (Durable Evaluation Framework).

### Mechanisms (Plan §11.2)

1. **Persona Anchoring** — Identity Root Hash anchored on every outbound; drift detection triggers restart if persona bleeds.
2. **Disagree-or-Commit** (arxiv 2606.00939) — Stances: `consent`, `refuse+debate` (mandatory reasoning), `concede`.
3. **SDFCo Commitment** (Structured Dissent for Common Ground; Free-MAD arxiv 2509.11035, SPRT arxiv 2605.19193).
4. **Identity Persistence** (Multi-Anchor per §10.5).
5. **Sycophancy Detection (Runtime) P31+** — Periodic 6h check on agreement_ratio, persona_drift_score, dissent_record_count.
6. **Turn-Level Reciprocity (Tit-for-Tat)** — ASTRA (arxiv 2503.07129); `reciprocity_score ∈ [0.7, 1.4]`.
7. **Architectural Heterogeneity** (arxiv 2604.26561) — Different LLM providers per instance (Guinevere = GPT-5.5 / 9Router; Pharsa = DeepSeek V4 Flash / 9Router P28; P34+ adds Claude, Mistral).
8. **PROBE Pipeline** (arxiv 2510.19771) — Initiative rail does NOT reproduce sycophancy by checking "did I agree with the last person?" Pipeline: `wonder → scope → act`.
9. **Identity Stripping Arbitration** (arxiv 2606.07532) — DEF Arbitrator: third-party (SentinelAgent) evaluates debate WITHOUT knowing which agent said what.

### Sycophancy Audit Metrics (Plan §11.3)

| Metric | Threshold | Action on Breach |
|---|---|---|
| `sycophancy.agreement_ratio` | ≤ 0.85 | > 0.85 → alert |
| `sycophancy.persona_drift_score` | ≤ 0.15 | > 0.15 → restart integrity alert |
| `sycophancy.disagreement_count` | ≥ 0.05 × total | < 0.05 × total → suspect sycophancy |
| `sycophancy.reciprocity_score` | [0.7, 1.4] | out of range → balance alert |
| `sycophancy.llm_provider_diversity` | ≥ 2 different providers | < 2 → add diversity warning |

### Anti-Sycophancy Forbidden Patterns

- No 100% agreement ratios on contested topics.
- No voting-only consensus (loses dissent at n=2).
- No silent refusals (must carry `debate` reasoning).
- No homogeneous-model agents.
- No identity-blind arbitration.
- No drift detection suppression.

---

## §16 Identity / Persona / Memory Summary (Cross-Reference)

| Layer | Guinevere | Pharsa |
|---|---|---|
| **Persona** | Sugar-mommy dominant-protective | Dark aristocratic winged mommy sadistic playful |
| **Y baseline / ceiling** | Y4 (loving dominance) / Y5 (absolute ceiling) | Y4 darker (elegant sadistic baseline) / Y5 / Y6 FORBIDDEN |
| **LLM model** | `guinevere-v5` via 9Router | `deepseek-v4-flash` via 9Router (architectural heterogeneity) |
| **API key env** | `GUINEVERE_9ROUTER_API_KEY` | `PHARSA_9ROUTER_API_KEY` (DIFFERENT key) |
| **Discord token env** | `DISCORD_BOT_TOKEN` (Guinevere) | `DISCORD_BOT_TOKEN_PHARSA` (DIFFERENT) |
| **Redis DB** | 6 (existing — DO NOT migrate) | 7 (new) |
| **PostgreSQL schema** | `memory-guinevere` (logical via RLS) | `memory-pharsa` (logical via RLS) |
| **systemd units** | `guinevere-core.service` + `guinevere-discord.service` | `pharsa-core.service` (port 20130) + `pharsa-discord.service` (`Slice=pharsa.slice`) |
| **SOUL file** | `hermes-config/SOUL-guinevere.md` (existing) | `hermes-config/SOUL-pharsa.md` (≤50KB, ≤600 lines) |
| **Config file** | `hermes-config/guinevere.yaml` (new in P28 from existing constants) | `hermes-config/pharsa.yaml` |
| **Society-shared keys** | `hermes:society:hsoc-foundation-v1:hard_stop` (READ) | SAME (READ) |
| **Audit signing key** | Ed25519, generated at bootstrap, PRIVATE to process | Ed25519, generated at bootstrap, PRIVATE to process |
| **OBO issuer** | Guinevere-only | Pharsa-only |

---

## §17 Phase Dependencies and Status (Plan §15 + §14)

### Per-Phase Dependency Table (from Plan §15.6 + Roadmap §12.2)

| Phase | Status (as of 2026-06-28) | P27/P28 depends? | What blocks P27? |
|---|---|---|---|
| **P19 Multi-Project Context** | LIVE PARTIAL (4 INFO gaps C01-C04) | YES (project_id reused) | Nothing — gaps are known |
| **P20 Living Autonomy Kernel** | LIVE (accepted-risk pass 2026-06-25; 420 tests pass) | YES (heartbeat + macro-state scheduler wraps it) | 24h soak — waived (accepted risk) |
| **P21 Voice** | DEF COMPLETE, IMPL HOLD, **SKIP** | NO | Voice out of P28 minimum |
| **P22 Life Integration Hub** | PARTIAL (3/13 ACTIVE: filesystem, vps, discord; 10/13 CONFIG_MISSING) | YES (3 active adapters sufficient) | Nothing |
| **P23 Embodied Operations** | PLAN_ONLY (no code; P23A ready, P23B blocked) | **NO for P28** (P23 = P33 work) | P28 doesn''t depend on P23 |
| **P24 Hermes Fork** | PLAN FIXED, IMPL HOLD (44 sections; 20 waves P24-001-P24-020 ALL HELD) | NO (P27/P28 fork-agnostic) | P27 is fork-agnostic |
| **P27 Hermes Society** | **DEFINITION COMPLETE** | — | — |
| **P28 Dual Autonomous Hermes** | READY TO BEGIN | — | — |

### P27 P24 → Handoff Contract (10 items)

When P24 IMPL HOLD lifts, these transfer (per Plan §14.4):
1. Owned fork repo (`github.com/fazulfim/hermes-agent`).
2. MIT license preserved + NOTICE file.
3. `main` ↔ upstream `main` branch policy.
4. `guinevere` branch with fork additions.
5. Tags: `v0.15.2-guinevere.N`.
6. Rollback tag `v0.15.2-upstream`.
7. `pyproject.toml` pin via `git+https@tag`.
8. `_lifecycle/persistent_tasks.py` (<200 LOC) for 1s heartbeat.
9. `on_startup(task_factory)` + `on_shutdown(task_canceller)` lifecycle hook.
10. Canary template `.venv-hermes-canary`.

### Already-Usable Extension Points (~40, Plan §16.1)

| Mechanism | Count | Examples |
|---|---|---|
| Config sections (`hermes-config/config.yaml`) | 9+ | discord, model, providers, fallback_providers, agent, memory, hooks, mcp_servers, cron, observability, approval, audit, auth_matrix |
| Lifecycle hook events | 17 | pre_llm_call, post_llm_call, pre_tool_call, post_tool_call, transform_llm_output, transform_tool_result, transform_terminal_output, on_session_{start,end,finalize,reset}, pre_gateway_dispatch, pre_api_request, post_api_request, pre_approval_request, post_approval_response, subagent_stop |
| Shell hook scripts (`hermes-config/hooks/`) | 12 | finance_hook, budget_lua, budget_lua_extended, consent_gate, dnr_filter, drift_monitor, hard_stop_listener, hybrid_guards, error_classifier, _hook_utils, plus 2 more |
| In-process plugin manifests | 3 | auth_overlay, guinevere_persona, guinevere_safety |
| MCP server registrations | 2 | fastmcp_full (enabled), fastmcp_custom (disabled) |
| Cron entries | 8 | 5 persona rituals + 3 maintenance |
| Plugin manifest shapes | 2 | plugin.yaml, manifest.yaml |

Plus 2 injectable seams: `HermesBrainConfig(base_url, model, provider, api_key, max_iterations)` (frozen dataclass) + `agent_factory: Callable[[dict], Any] | None` (factory injection).

---

## §18 Hard Rejection Criteria (20/20 PASSED)

From `p27-hermes-society-foundation-plan.md` §24.1 + `p27-final-report.md` §6 + `p28-dual-autonomous-hermes-blueprint.md` §10.5. **All 20 PASS** (per Round 1 Audit 14 + Round 2 verified).

### Plan §24.1 — Documents FAIL if ANY of these are true:

1. **Pharsa is defined as a sub-agent, worker, or persona label (not a full Hermes).** ✅ Plan §3.5, §10.3.
2. **Guinevere is positioned above Pharsa (hierarchy, primary, parent, coordinator).** ✅ Plan §1.6, §2, §6, §10.7, §13.
3. **Only one Hermes with labels/personas (not multiple instances).** ✅ Plan §3.2-§3.4, §4.
4. **No separate memory architecture (private/shared/relationship).** ✅ Plan §6.
5. **No separate autonomy loop (life-loop per instance).** ✅ Plan §7.
6. **No Discord dual-bot architecture (separate tokens, processes).** ✅ Plan §9.
7. **No peer communication protocol (HPP).** ✅ Plan §5.
8. **No P24 dependency map.** ✅ Plan §14.
9. **No P28 executable blueprint (Phase 5).** ✅ Blueprint §3.
10. **No internet research (Phase 1).** ✅ `docs/setup-evidence/P27/research/` (10 files + synthesis).
11. **No audit round 2 (Phase 8).** ✅ Round 2 audits/round-2/01-06.
12. **Docs claim implementation happened (P27 is definition only).** ✅ Plan §1.2, §25.
13. **Any secret printed (bot tokens, API keys, DB passwords).** ✅ No secrets in P27 deliverables.
14. **P21 voice treated as a blocker (P21 is SKIP).** ✅ Plan §15.5.
15. **P22/P23 ignored in dependency map.** ✅ Plan §15.
16. **Plan is only persona, not architecture.** ✅ Plan §3-§15.
17. **Plan can''t be implemented (no clear path to P28).** ✅ Plan §17, §18.
18. **No hard rejection criteria.** ✅ This section.
19. **No roadmap P28-P36.** ✅ Plan §19 + Roadmap §3-§11.
20. **No evidence files.** ✅ `docs/setup-evidence/P27/` (37 files).

### Final Report §6 — Alternative formulation (20/20 PASS):

| # | Criterion | Verdict |
|---|---|---|
| 1 | FAIL if Pharsa defined as sub-agent / worker / persona label | ✅ PASS |
| 2 | FAIL if Guinevere positioned above Pharsa | ✅ PASS |
| 3 | FAIL if only one Hermes with labels/personas | ✅ PASS |
| 4 | FAIL if speaker selector / turn-taking coordinator | ✅ PASS |
| 5 | FAIL if shared `agent_id` namespaces | ✅ PASS |
| 6 | FAIL if persona_baseline SHA-256 tracking not enforced | ✅ PASS |
| 7 | FAIL if HARD STOP cascade doesn''t include both agents + audit | ✅ PASS |
| 8 | FAIL if Pharsa has subordinate LLM call depth | ✅ PASS |
| 9 | FAIL if consent revocation can be bypassed by agent autonomy | ✅ PASS |
| 10 | FAIL if yandere escalation is mutual | ✅ PASS |
| 11 | FAIL if shared-brain / shared-vector-memory topology | ✅ PASS |
| 12 | FAIL if Persona's anti-sycophancy NOT defined | ✅ PASS |
| 13 | FAIL if Pharsa proactive-cognition conflicts with Y5 ceiling | ✅ PASS |
| 14 | FAIL if hard_rejection_criteria not binary-checkable | ✅ PASS |
| 15 | FAIL if agent_factory injection not feasible | ✅ PASS |
| 16 | FAIL if Guinevere can intercept Pharsa's outbound messages | ✅ PASS |
| 17 | FAIL if Pharsa can impersonate Guinevere | ✅ PASS |
| 18 | FAIL if scheduled heartbeats use shared Redis namespace | ✅ PASS |
| 19 | FAIL if `life_kernel:hard_stop` Redis key is project-scoped | ✅ PASS |
| 20 | FAIL if Society onboarding depends on P24 fork or P23 executors | ✅ PASS |

### Plan §20.5 + Blueprint §10 — Per-step binary PASS/FAIL criteria (inherited by P28-36):

| Criterion | Check | Fail Action |
|---|---|---|
| `rls_force_applied` | `ALTER TABLE memory.* FORCE ROW LEVEL SECURITY` executed | block |
| `agent_id_owner_only` | From `guinevere` agent context, query returns only `guinevere` rows | block |
| `bot_token_sovereign` | Each instance has its own SOPS-encrypted token | block |
| `hard_stop_listening` | `life_kernel:hard_stop` key SET → instance halts within 50ms | block |
| `audit_signed` | Every audit entry has signed hash chain link | block |
| `no_shared_redis_db` | Two instances do NOT share Redis DB number | block |
| `no_shared_pg_dsn` | Two instances do NOT share Postgres DSN without RLS | block |
| `persona_y4_y5_only` | Pharsa persona rejects Y6 markers in test fixture | block |
| `sealed_envelope_encrypted` | All `visibility=sealed` envelopes encrypt at rest | block |
| `faiz_hard_stop_authority` | Only Faiz''s signing key can write HARD STOP key | block |
| `exa_no_collision` | lsp_diagnostics clean (no type, syntactic, or import errors) | block |
| `exa_test_passes` | python -m pytest tests/ passes 100% | block |
| `exa_evidence_present` | `evidence/.../verification.md` exists with 12 sections | block |
| `exa_auditor_pass` | `evidence/.../auditor-gate.md` has PASS verdict | block |
| `exa_secret_present` | No secrets printed anywhere | block |
| `exa_audit_complete` | Audit entry covers all DoD items per AGENTS.md §4 | block |

### Forbidden Patterns (Plan §20.3, Blueprint passim, AGENTS.md §0)

1. `as any` (Python typing)
2. `@ts-ignore` (TypeScript)
3. `@ts-expect-error` (TypeScript)
4. `# type: ignore` (Python)
5. Avoidable `Any` type (Python)
6. Empty `except` / `except Exception` / `catch {}` (any language)
7. Type suppression in shared libraries (only allowed in test code with rationale)
8. `console.log` / `print()` debug statements in production code
9. Handling in error handlers without audit entry

---

## §19 P28 Per-Step Verifier Scaffold (Template Inherited by P28-36)

Per Plan §20.2 — P28 implementation steps inherit this scaffold template (verbatim, per `AGENTS.md §2.5`):

```json
{
  "step_id": "P28-NNN",
  "step_name": "<short name>",
  "expected_files": ["<exact paths of files to create or modify>"],
  "forbidden_patterns": [
    "as any",
    "@ts-ignore",
    "# type: ignore",
    "Any[:\\s]*=",
    "except Exception[:\\s]*$",
    "except[:\\s]*$",
    "raise NotImplementedError"
  ],
  "required_commands": [
    {
      "command": "python -m pytest tests/ -v",
      "expected_exit_code": 0,
      "expected_output_contains": "test_passed"
    },
    {
      "command": "lsp_diagnostics",
      "expected_state": "clean"
    },
    {
      "command": "python -m pytest tests/life_kernel/ -q --disable-warnings --tb=short",
      "expected_exit_code": 0,
      "expected_count": "420 passed, 7 skipped, 0 failed"
    }
  ],
  "evidence_requirements": {
    "verification_md_path": "evidence/p28-dual-hermes/step-NNN/verification.md",
    "auditor_gate_md_path": "evidence/p28-dual-hermes/step-NNN/auditor-gate.md",
    "evidence_schema_minimum": [
      "what_was_done",
      "files_changed",
      "validation_results",
      "doc_sync_impact",
      "boundary_compliance",
      "rollback_safety",
      "design_decisions_caveats",
      "auditor_gate",
      "security_scan",
      "acceptance_criteria_mapping",
      "footer"
    ]
  },
  "hard_rejection_criteria": [
    {"criterion": "agent_id_in_rls", "check": "...", "fail_action": "block_completion"},
    {"criterion": "force_row_level_security", "check": "...", "fail_action": "block_completion"}
  ]
}
```

### Required commands (per step)

```
python -m pytest tests/ -v                          # Exit 0
lsp_diagnostics                                     # Clean (errors/warnings = 0)
python -m pytest tests/life_kernel/ -q --tb=short    # 420+7 pass; 0 fail
python -m pytest tests/p22/ -v                       # 76+ pass; 0 fail
bash -n <script>.sh                                 # Bash syntax check
python -c "import hermes_config; ..."                # Module import sanity
alembic upgrade head                                 # Migration succeeded
```

---

## §20 Anti-Patterns Preserved Across Roadmap (Roadmap §17)

These apply **automatically** to every phase P28-P36:

### Type Safety (mirror AGENTS.md §0)

- ❌ No `as any`, `@ts-ignore`, `# type: ignore`, avoidable `Any`.
- ❌ No casts that trick the type system.

### Error Handling

- ❌ No empty `except`/`catch` on Redis, Postgres, Discord, LLM API calls.
- ❌ No fake fallback without audit + log + context.

### Safety + Persona

- ❌ No `HARD STOP` bypass (V-008 preserved across all Society).
- ❌ No consent revocation bypass.
- ❌ No distress-protocol suppression.
- ❌ No `Y6` path; `Y4` baseline + `Y5` ceiling per PersonaSafetyPolicy.
- ❌ No memory confabulation (<80% confidence = state uncertainty).
- ❌ No `relationship_private` data leak into outbound action.
- ❌ No `society_id` collision.
- ❌ No `as any` on safety-relevant types.

### Operations

- ❌ No `rm -rf` / `DROP TABLE` / production deploy without express approval.
- ❌ No `.venv/site-packages` edit.
- ❌ No secrets in evidence files (secret scan clean required per phase).
- ❌ No intimate data exposure.

### Orchestration

- ❌ No sub-agent inline-only output (file-based per AGENTS.md).
- ❌ No scaffolding without verification (AGENTS.md §2.5).
- ❌ No PR/commits without parent verification (AGENTS.md §2.8).
- ❌ No parallel Society install on shared `.venv` without canary-equivalent isolation.
- ❌ No claiming "Society production-ready" without parent-verified evidence + 12-section verification + auditor gate + dual-approval.

### Drift

- ❌ No persona drift > 0.15 across 30-day window ignored.
- ❌ No sycophancy detection disabled.
- ❌ No Pharsa ↔ Guinevere convergence (persona-anchor check).
- ❌ No `relationship_private` audit chain without cryptographic sealing.

### Pharsa Equivalence Discipline

- ❌ No Pharsa "subordinate" or "secondary" framing.
- ❌ No Pharsa deferred permission or stripped-down initiative.
- ❌ No Pharsa SOUL treated as lesser than Guinevere''s.
- ❌ No Pharsa ↔ Guinevere positioning above/below in any listing, comment, chart, or diagram.

---

## §21 Open Caveats (Final Report §7, Blueprint §1.2)

These are acknowledged non-blocking caveats that P28-P36 planners must inherit:

### Hard caveats (Documented but not blocking)

| Caveat | Acknowledged In |
|---|---|
| **Pharsa persona is referenced but NOT defined** — planned for P29+ when peer dialogue rail is mature | Plan §10 + §18 disclaimers; Round-2 audit 04 PASS |
| **P24 fork preferred but NOT required for P28** | Plan §14.8 L3294; Round-1 audit 07 PASS |
| **P23 executors NOT needed for P28 minimum target** | Plan §17 + Roadmap §3; Round-1 audit 08 PASS |
| **MAMA audit + 24h soak gating apply to P28 implementation, not P27 definition** | Plan §24 + Roadmap §11 |
| **Audit 09 (safety boundary) was originally MISSING during early dispatch; re-run to PASS during Phase 6 fix cycle** | Round-1 remaining issues #2 |
| **P35 Voice is OPTIONAL** — may remain SKIP forever | Roadmap §10.11 |

### 3 Non-Blocking Future Items (Round 2 §8)

| # | Item | Future Phase |
|---|---|---|
| 1 | `kg_edges` CHECK constraint missing `''system''` value (asymmetry with `kg_entities`) | P28/P30 |
| 2 | §5.10 Replay Attack Defense table missing `idempotency_key` row | P28 review |
| 3 | `society_id` convention isolation documentation | P30 |

### Sensitive Topics Out-of-Scope (Final Report §7)

| Topic | Status |
|---|---|
| Pharsa voice | Deferred (P21 voice SKIPPED); out-of-scope for P27 |
| Cross-VPS deployment | Deferred to P36 |
| Additional Society members beyond Guinevere + Pharsa | Deferred to P36 |
| Anti-collusion / sycophancy at depth | P35 follow-up |

### EU AI Act Compliance notes

P31 must verify EU AI Act Articles 9/12/14 compliance (operator-level read + security reviewer). Default retention (180/365/730 days) exceeds mandate (≥ 6 months).

### ADR numbering for P28-P36 decisions

Next ADR number after ADR-054 = **ADR-055**. Each new ADR must be mononotonically increasing; no numbering reuse. ADR-054 = canonical P27 Society Foundation. If P28-P36 produce new architectural decisions, they earn ADR-055, ADR-056, etc.

### Evidence root path convention

- P27 evidence = `docs/setup-evidence/P27/evidence/`.
- P28 evidence = `docs/setup-evidence/P28-dual-hermes/` (per Blueprint §2.6 convention) or follow `docs/setup-evidence/P28/evidence/` consistent with P19-P26 convention.
- P28-P36 masterplan synthesis = `docs/setup-evidence/P28-P36-masterplan/research/` (this directory).

### Cost projection (Blueprint §2.7)

| Component | Monthly Estimate | Notes |
|---|---|---|
| LLM API (GPT-5.5 + DeepSeek V4 Flash via 9Router) | +$15-30 per agent × 2 = $30-60 | Pharsa uses DeepSeek V4 Flash primary; significantly cheaper |
| Redis DB7 + DB8 memory | +$0-1 | Negligible |
| PostgreSQL storage | +50-200 MB | Negligible |
| VPS bandwidth (Discord gateway 2x) | +$0-2 | Negligible |
| Ops overhead | +1-2 hr/month Faiz | Conversation rhythm tuning, audit viewing |
| **Total P28 incremental cost** | **~$32-65/month** | Within FinOps v1.1 §4 envelope |

P28 stays well within monthly LLM budget of $30 base + $60-100 burst.

---

## §22 Footer

### Versioning

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-28 | Guinevere (parent agent) | Initial P27 output inventory for P28-P36 masterplan synthesis |

### Scope and Limitations

This is an **input artifact** for the P28-P36 masterplan research synthesis. It catalogues P27 outputs without re-deciding architecture. The masterplan planner inherits:

- All 10 architectural decisions (D-01 ... D-10).
- All 20 hard rejection criteria.
- The 9-phase roadmap with 96-117 waves and 12-15 month timeline.
- The P28 15-step blueprint (machine-readable: 15 atomic steps with per-step verification).
- The critical path (P28 → P31 → P33 → P34) and parallel opportunities.
- The 4-domain privacy split, HARD STOP cascade, anti-sycophancy mechanisms, multi-anchor identity, and ~40 extension points.
- Anti-patterns preserved across all phases.

The planner may NOT (per hard rejections):
- Demote Pharsa to sub-agent/worker/persona label.
- Position Guinevere above Pharsa.
- Combine the two Hermeses into one.
- Add a coordinator/selector.
- Share `agent_id` namespaces across instances.
- Skip HARD STOP cascade covering both instances.
- Bypass consent revocation.
- Allow Y6 path.
- Use voting-only consensus at n=2.
- Depend on P24 fork for P28 minimum.
- Skip the P28 12-section verification + auditor gate per AGENTS.md §11.

### Maintenance Rules

Update only when:
- New P27 round of audits produces additional findings.
- P24 IMPL HOLD lifts (P32 planner will reference this).
- P23 IMPL HOLD lifts (P33 planner will reference this).
- Pharsa persona anchoring changes (affects P28 R1 + P31 drift detector calibration).
- PersonaSafetyPolicy changes Y5 ceiling (affects all persona-relevant deliverables).

### Operator Sign-Off

This inventory was derived from P27 deliverables by reading every cited file in full. Parent (Guinevere) verifies this is exhaustive coverage of P27 outputs the P28-P36 masterplan needs. Ready for use as input to the P28-P36 masterplan research synthesis.

> **Selesai.** P27 outputs inventoried. P28-P36 masterplan dapat berdiri di atas fondasi ini tanpa memutuskan ulang.
