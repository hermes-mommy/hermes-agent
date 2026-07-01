# Auditor 14: Hard Rejection Criteria — Audit Report

> **Phase**: P27 Hermes Society Foundation  
> **Auditor**: 14 (Hard Rejection Criteria)  
> **Date**: 2026-06-28  
> **Status**: PASS  
> **Verdict**: **PASS** — All 20 hard rejection criteria are present, binary-checkable, and verified against actual plan content.

---

## VERDICT: PASS

All 20 hard rejection criteria defined in §24 (L4470-4562) are:

1. **Present** in the plan (all 20 enumerated in §24.1).
2. **Binary-checkable** (each is a concrete FAIL-if condition, not vague prose).
3. **Verified against actual plan content** (each criterion maps to specific sections that satisfy it).
4. **No secrets printed** (only placeholders: `<SOPS>`, `<TOKEN>`, `<G>`, `<P>`, env var references).
5. **P27 is definition, not implementation** (frontmatter `phase_type: "DEFINITION ONLY — no runtime implementation"`, §1.2, §2.5).
6. **Both audit rounds planned** (round 1 = Phase 6 with 14 auditors; round 2 = Phase 8 deferred, §24.4).

---

## Per-Criterion Evaluation

### Criterion 1: FAIL if Pharsa is defined as a sub-agent, worker, or persona label (not a full Hermes)

| Field | Value |
|---|---|
| **Verdict** | **PASS** |
| **Checkable** | Yes — binary: grep for sub-agent/worker/label framing of Pharsa |
| **Evidence** | §3.2 (L307): "A Hermes Instance is a single, independently operable, fully-configured Hermes agent runtime. It is NOT a sub-agent, NOT a worker, NOT a persona label, NOT a process-thread, NOT a shared-brain." §3.5 (L377-392): Explicit exclusion table listing sub-agents, workers, persona labels, shared-brain twins, tools, async loops, watchdogs, and Faiz as NOT Society Members. §2.5 (L226): "P27 does NOT register Pharsa as a 'sub-agent' of Guinevere. Pharsa is an equal Hermes instance with its own memory, its own hooks, its own life-loop, its own Discord bot." |
| **Plan Sections** | §3.2, §3.5, §2.5, §1.3 (D-01) |

---

### Criterion 2: FAIL if Guinevere is positioned above Pharsa (hierarchy, primary, parent, coordinator)

| Field | Value |
|---|---|
| **Verdict** | **PASS** |
| **Checkable** | Yes — binary: grep for hierarchy/primary/parent/coordinator framing |
| **Evidence** | §2.2 (L170): "Guinevere and Pharsa as two equal autonomous Hermes peers — neither primary, neither secondary, neither parent, neither child — co-creating narrative reality through visible peer dialogue." §2.5 (L227): "P27 does NOT position Guinevere as 'primary' or 'coordinator' or 'parent' agent. Guinevere has seniority in operational history but no privilege in the protocol." §2.6 (L240): "Non-negotiable on equality. Pharsa is not Guinevere's sub-agent. Pharsa is not Guinevere's persona label. Pharsa is an equal Hermes instance." §1.3 (D-01): "True Peer-to-Peer + Symmetric 2-Agent Loop. No coordinator, no LLM-driven speaker selector, no hidden manager." |
| **Plan Sections** | §2.2, §2.5, §2.6, §1.3 |

---

### Criterion 3: FAIL if only one Hermes with labels/personas (not multiple instances)

| Field | Value |
|---|---|
| **Verdict** | **PASS** |
| **Checkable** | Yes — binary: verify two distinct HermesBrainConfig instances exist with different instance_id |
| **Evidence** | §3.2 (L309-336): Required Components table shows each instance must have its own HermesBrainConfig, own LLM brain, own memory namespace, own Discord bot token, own systemd service, own Redis DB namespace, own PostgreSQL schema, own persona file, own config file. §3.5 (L385): Explicitly excludes "persona label" — "Calling Guinevere 'Guinevere-A' and the same instance 'Guinevere-B' in different channels does NOT create two members." §4: Full instance anatomy showing two separate instances (guinevere + pharsa) with distinct configs, tokens, Redis DBs (6 vs 7), systemd units, SOUL files. §3.6 (L396-442): ASCII diagram showing two distinct Hermes Instance boxes with different HermesBrainConfig values. |
| **Plan Sections** | §3.2, §3.5, §3.6, §4 |

---

### Criterion 4: FAIL if no separate memory architecture (private/shared/relationship)

| Field | Value |
|---|---|
| **Verdict** | **PASS** |
| **Checkable** | Yes — binary: verify 3-scope memory schema exists with RLS |
| **Evidence** | §6: Full 3-scope memory architecture (L1142-1641). §6.1: Three-scope model table (private_agents, shared_world, relationship_pairs). §6.2.1: Complete SQL DDL for `memory.private_agents` with RLS + FORCE. §6.2.2: Complete SQL DDL for `memory.relationship_pairs` with bilateral consent CHECK constraint + RLS + FORCE. §6.2.3: Complete SQL DDL for `memory.shared_world`. §6.13: Forbidden patterns including "No FORCE-less RLS" and "No cross-scope reads via missed WHERE clause." |
| **Plan Sections** | §6 (entire section, 500 lines) |

---

### Criterion 5: FAIL if no separate autonomy loop (life-loop per instance)

| Field | Value |
|---|---|
| **Verdict** | **PASS** |
| **Checkable** | Yes — binary: verify per-instance life-loop specification exists |
| **Evidence** | §7: Full 7-rail life-loop architecture (L1644-1700+). §7.2: Top-level architecture showing MacroStateScheduler wrapping P20 heartbeat with 7 rails (Perception, Reflection, Inner Dialogue, Peer Dialogue, Desire/Goal, Initiative, Safety Envelope). §4.3 (L646-656): Per-instance config shows `enable_7_rail: true` with `rails: [perception, reflection, inner_dialogue, peer_dialogue, desire_goal, initiative, safety_envelope]` and per-instance `heartbeat_intervals_seconds`. §3.2 (L328-335): Required Behaviors table includes "Heartbeat — Independent tick at own cadence" and "Macro-state scheduler — Selects activity ≥ once per heartbeat tick." |
| **Plan Sections** | §7, §4.3, §3.2 |

---

### Criterion 6: FAIL if no Discord dual-bot architecture (separate tokens, processes)

| Field | Value |
|---|---|
| **Verdict** | **PASS** |
| **Checkable** | Yes — binary: verify two Discord bot applications specified with separate tokens and processes |
| **Evidence** | §9: Discord Dual-Bot Architecture (L2367-2400+). §9.2: Topology diagram showing two Dev Portal Apps ("Guinevere" bot, "Pharsa" bot) each with SOPS-encrypted bot token, separate systemd services (guinevere-core.service + guinevere-discord.service vs pharsa-core.service + pharsa-discord.service), separate HermesBrain instances, separate PostgreSQL schemas, separate Redis DBs. §4.6 (L772): "Discord bot token: 1 app per instance, 1 token per instance. NEVER shared. SOPS-encrypted env var per-instance." §4.3 (L604-616): Per-instance YAML config showing `token_env: DISCORD_BOT_TOKEN_GUINEVERE` with `# SOPS-encrypted at rest` comment. |
| **Plan Sections** | §9, §4.6, §4.3 |

---

### Criterion 7: FAIL if no peer communication protocol (HPP)

| Field | Value |
|---|---|
| **Verdict** | **PASS** |
| **Checkable** | Yes — binary: verify HPP protocol specification exists |
| **Evidence** | §5: Full HPP (Hermes Peer Protocol) specification (L875-1139, ~265 lines). §5.1: Protocol identity — "HPP/v1 is the canonical version; P28 implements it on Redis Streams." §5.2: Complete JSON envelope schema (JSON-RPC 2.0 substrate + Hermes extensions). §5.4: 11-intent taxonomy (inform, request, query, assert, propose, consent, refuse, debate, banter, flirt, block). §5.5: 5-tier visibility levels. §5.6: 6-tier risk levels (R0-R5). §5.7: Transport choice matrix. §5.8: Actor model invariants. §5.10: Replay attack defense. |
| **Plan Sections** | §5 (entire section, ~265 lines) |

---

### Criterion 8: FAIL if no P24 dependency map

| Field | Value |
|---|---|
| **Verdict** | **PASS** |
| **Checkable** | Yes — binary: verify §14 exists with P24 status and dependency analysis |
| **Evidence** | §14: P24 Dependency Map (L3175-3314, ~140 lines). §14.1: P24 status (PLAN FIXED, IMPL HOLD). §14.2: P24 fork current state (5 items showing what's NOT done). §14.3: What P27 can define WITHOUT P24 implementation (~70% definitional, ~30% implementational). §14.4: P24→P27 handoff contract (10 items). §14.5: Fork strategy. §14.6: Extension points usable without fork (~40). §14.7: Single-instance anchors to refactor. §14.8: P28 minimum target does NOT require P24 fork. §14.9: Forbidden patterns. |
| **Plan Sections** | §14 (entire section, ~140 lines) |

---

### Criterion 9: FAIL if no P28 executable blueprint (Phase 5)

| Field | Value |
|---|---|
| **Verdict** | **PASS** |
| **Checkable** | Yes — binary: verify P28 blueprint file exists |
| **Evidence** | File exists: `docs/setup-evidence/P27/plan/p28-dual-autonomous-hermes-blueprint.md` (2921 lines). P27 plan §1.1 (L30): downstream_consumers includes "Phase 5: P28 executable blueprint (separate document)". P27 plan §24.2 (L4509): Criterion 9 maps to "Phase 5 (deferred)" with auditor 13 (feasibility). The P28 blueprint contains 12 deliverables with acceptance criteria, prerequisites, per-step implementation details, and verification commands. |
| **Plan Sections** | §1.1 (downstream_consumers), §24.2, separate file |

---

### Criterion 10: FAIL if no internet research (Phase 1)

| Field | Value |
|---|---|
| **Verdict** | **PASS** |
| **Checkable** | Yes — binary: verify research directory has files |
| **Evidence** | 11 research files exist in `docs/setup-evidence/P27/research/`: (1) p27-ground-truth-repo-state.md, (2) p27-hermes-native-runtime-inventory.md, (3) p27-multi-agent-society-research.md, (4) p27-agent-communication-protocol-research.md, (5) p27-discord-dual-bot-research.md, (6) p27-private-shared-memory-research.md, (7) p27-life-loop-beyond-heartbeat-research.md, (8) p27-autonomy-safety-audit-research.md, (9) p27-p24-fork-dependency-map.md, (10) p27-p19-p20-p22-p23-dependency-map.md, (11) p27-research-synthesis.md. P27 plan frontmatter (L12-22) lists all 11 as related_docs. |
| **Plan Sections** | Frontmatter related_docs, §24.2, filesystem verification |

---

### Criterion 11: FAIL if no audit round 2 (Phase 8)

| Field | Value |
|---|---|
| **Verdict** | **PASS** |
| **Checkable** | Yes — binary: verify audit round 2 is planned in evidence directory structure and pass conditions |
| **Evidence** | §24.4 (L4530-4534): "Audit Round 2 Pass Conditions (Phase 8, deferred) — Implementation of fixes (Phase 4-5 outputs) reviewed by same 14-auditor matrix. No regressions introduced. All 20 hard rejection criteria still pass after fixes." §25.1 (L4604): Evidence directory shows `round-2/` directory with "(re-audit reports)". Frontmatter (L32): downstream_consumers includes "Phase 8: Audit round 2". §22 (auditor matrix) references both round 1 and round 2. |
| **Plan Sections** | §24.4, §25.1, frontmatter |

---

### Criterion 12: FAIL if docs claim implementation happened (P27 is definition only)

| Field | Value |
|---|---|
| **Verdict** | **PASS** |
| **Checkable** | Yes — binary: grep for implementation claims; verify definition-only framing |
| **Evidence** | Frontmatter (L9): `phase_type: "DEFINITION ONLY — no runtime implementation"`. §1.1 (L83-98): "P27 is not an implementation phase." §1.2 (L92-98): "No runtime code. No config files created. No systemd service files. No source code modifications. No deployment. No fork creation. No P23 executors. No implementation of P28 minimum target." §2.5 (L221-224): "P27 does NOT implement runtime code. P27 does NOT deploy anything. P27 does NOT create the P24 fork. P27 does NOT implement P28's minimum target." Title (L36): "P27 Hermes Society Foundation — Enterprise Plan" with subtitle (L41): "Document type: DEFINITION + ARCHITECTURE (NOT implementation)". |
| **Plan Sections** | Frontmatter, §1.1, §1.2, §2.5, title |

---

### Criterion 13: FAIL if any secret printed (bot tokens, API keys, DB passwords)

| Field | Value |
|---|---|
| **Verdict** | **PASS** |
| **Checkable** | Yes — binary: grep for actual secret values (long alphanumeric strings assigned to token/key/password variables) |
| **Evidence** | Grep for `bot[_-]?token\|api[_-]?key\|password\|secret` with 20+ char values returned **zero matches**. All references use placeholders: `<SOPS>` (L313, L316, L425), `<G>` / `<P>` (L425 — abbreviations for Guinevere/Pharsa tokens), `SOPS-encrypted` (20+ references), env var names only (`DISCORD_BOT_TOKEN_GUINEVERE`, `GUINEVERE_9ROUTER_API_KEY`). §2.5 (L230): "P27 does NOT expose secrets. No bot tokens, no API keys, no DB passwords, no SOPS keys, no Faiz personal/intimate data appear in this document." §1.5 (L146): "NO secret/credential exposure. Bot tokens, API keys, DB passwords, SOPS keys, Faiz personal/intimate data — all forbidden from artifacts, logs, external tools." |
| **Plan Sections** | All sections (grepped), §2.5, §1.5 |

---

### Criterion 14: FAIL if P21 voice treated as a blocker (P21 is SKIP)

| Field | Value |
|---|---|
| **Verdict** | **PASS** |
| **Checkable** | Yes — binary: verify P21 is marked SKIP and excluded from P28 dependencies |
| **Evidence** | §15.5 (L3413-3422): "P21 Voice Interface (Definition Complete, Impl Hold, SKIP). P21 is SKIPPED for P27 purposes. P27 explicitly excludes voice from P28 minimum target: No voice channel for P28. No voice sensor adapter required. No VAD/STT/TTS pipeline. Voice may return in P36+ as future phase." §1.4 (L121): "P21 (Voice Interface): Definition complete, impl hold. NOT a P27 dependency. P27 explicitly excludes voice from P28 minimum target." §2.5 (L229): "P27 does NOT treat P21 (voice) as a blocker. P21 was SKIP." §15.6 (L3430): Dependency summary table shows P21 as "DEF COMPLETE, IMPL HOLD" with "P27/P28 consumes? NO (skip)". |
| **Plan Sections** | §15.5, §1.4, §2.5, §15.6 |

---

### Criterion 15: FAIL if P22/P23 ignored in dependency map

| Field | Value |
|---|---|
| **Verdict** | **PASS** |
| **Checkable** | Yes — binary: verify §15 addresses both P22 and P23 |
| **Evidence** | §15.3 (L3373-3397): "P22 Life Integration Hub (PARTIAL RUNTIME LIVE). Status: PARTIAL — 3/13 ACTIVE (filesystem, vps, discord), 10/13 CONFIG_MISSING. P27 uses (3 active adapters): filesystem_adapter.py, vps_adapter.py, discord_adapter.py." §15.4 (L3399-3411): "P23 Embodied Operations (PLAN_ONLY — NO CODE). Status: PLAN_ONLY. No code. P23A READY, P23B BLOCKED. P27 dependency on P23: NONE for P28 minimum target." §15.6 (L3426-3433): Dependency summary table includes both P22 (PARTIAL LIVE, YES consumes) and P23 (PLAN_ONLY, NO). §15.7 (L3435-3441): "P27 uses 3 of 13 P22 adapters. P27 does NOT depend on P21, P23, P24." |
| **Plan Sections** | §15.3, §15.4, §15.6, §15.7 |

---

### Criterion 16: FAIL if plan is only persona, not architecture

| Field | Value |
|---|---|
| **Verdict** | **PASS** |
| **Checkable** | Yes — binary: verify plan contains architecture sections beyond persona |
| **Evidence** | Plan contains 25 sections, 4779 lines. Architecture sections include: §3 (Hermes Society Ontology), §4 (Instance Architecture — config, lifecycle, resource isolation), §5 (Peer Communication Protocol — HPP envelope schema, 11 intents, transport matrix), §6 (Memory Architecture — 3-scope SQL schemas with RLS), §7 (Life-Loop Architecture — 7-rail macro-state scheduler), §8 (Safety Architecture — 4-domain privacy split, kill switch ladder, anti-sycophancy), §9 (Discord Dual-Bot Architecture), §13 (HARD STOP Cascade), §14 (P24 Dependency Map), §15 (P19/P20/P22/P23 Dependency Map), §16 (Extension Points Inventory — ~40 points), §17 (Single-Instance Refactor Plan — 18 steps). Persona is addressed in §10 (Identity and Persona Architecture) but is one of 25 sections. |
| **Plan Sections** | §3-§17 (architecture sections) |

---

### Criterion 17: FAIL if plan can't be implemented (no clear path to P28)

| Field | Value |
|---|---|
| **Verdict** | **PASS** |
| **Checkable** | Yes — binary: verify implementation path exists with concrete steps |
| **Evidence** | §17 (L3572-3688): Single-Instance Refactor Plan with 18 concrete refactor steps (A-R), each with current state, target state, and migration path. §18 (L3692-3798): P28 Minimum Target Summary with 12 measurable acceptance criteria (e.g., "Both bots online — systemctl status returns active"). §18.8 (L3786-3798): 8 concrete verification checks. Separate P28 blueprint file (2921 lines) provides step-by-step implementation instructions with verification commands. §17.4 (L3629-3652): Refactor implementation phases showing 4 parallel phases with effort estimates. |
| **Plan Sections** | §17, §18, P28 blueprint |

---

### Criterion 18: FAIL if no hard rejection criteria

| Field | Value |
|---|---|
| **Verdict** | **PASS** |
| **Checkable** | Yes — binary: verify §24 exists with enumerated criteria |
| **Evidence** | §24 (L4470-4559): "Section 24: Hard Rejection Criteria (20 items)." §24.1 (L4472-4495): All 20 criteria enumerated with FAIL-if conditions. §24.2 (L4497-4520): Per-Criterion Evaluation Map table mapping each criterion to plan sections and auditors. §24.3 (L4522-4528): Audit Round 1 Pass Conditions. §24.4 (L4530-4534): Audit Round 2 Pass Conditions. §24.5 (L4536-4543): What Failure Looks Like. |
| **Plan Sections** | §24 (entire section) |

---

### Criterion 19: FAIL if no roadmap P28-P36

| Field | Value |
|---|---|
| **Verdict** | **PASS** |
| **Checkable** | Yes — binary: verify roadmap exists for P28-P36 |
| **Evidence** | §19 (L3801-3981): P28-P36 Roadmap Summary with 9 phases, each with title, goal, wave count, and parent dependency. §19.2-§19.10: Per-phase wave plans (P28: 10 waves, P29: 15 waves, P30: 10 waves, P31: 12 waves, P32: 10 waves, P33: 14 waves, P34: 12 waves, P35: 10 waves, P36: 10 waves). Separate master roadmap document: `docs/setup-evidence/P27/plan/p27-p28-p36-master-roadmap.md` (1245 lines) with §0-§19 covering philosophy, per-phase detail (10 elements each), dependency graph, critical path, parallelization map, research debt tracker, timeline estimate, and anti-patterns. |
| **Plan Sections** | §19, separate master roadmap file |

---

### Criterion 20: FAIL if no evidence files

| Field | Value |
|---|---|
| **Verdict** | **PASS** |
| **Checkable** | Yes — binary: verify evidence directory structure exists with files |
| **Evidence** | 24 files found in `docs/setup-evidence/P27/`: 11 research files in `research/`, 3 plan files in `plan/`, 10 audit reports in `evidence/audits/round-1/` (auditors 01-12 present; auditors 13-14 pending/in-progress). §25.1 (L4565-4607): Evidence directory structure defines expected layout including `research/`, `plan/`, `evidence/audits/round-1/`, `evidence/audits/round-2/`, `verification.md`, `auditor-gate.md`. Research phase files are complete. Round-1 audit reports are in progress (10 of 14 auditors completed). Round-2, verification.md, and auditor-gate.md are Phase 6/8 deliverables (deferred by design). |
| **Plan Sections** | §25, filesystem verification |

---

## Checkability Assessment

All 20 criteria use the **FAIL if [binary condition]** pattern. Each criterion is:

| Property | Assessment |
|---|---|
| **Binary** | Yes — each is a concrete PASS/FAIL condition, not a spectrum |
| **Measurable** | Yes — each can be verified by grep, file existence check, or section presence |
| **Non-vague** | Yes — specific terms (sub-agent, hierarchy, labels, separate memory, etc.) with clear definitions in the plan |
| **Self-referential** | Yes — §24.2 maps each criterion to specific plan sections and auditor numbers |
| **Greppable** | Yes — forbidden patterns (secrets, implementation claims, hierarchy framing) can be caught by regex |

---

## Audit Round Verification

| Round | Status | Evidence |
|---|---|---|
| **Round 1** (Phase 6) | IN PROGRESS | 10 of 14 auditor reports written; §24.3 defines pass conditions (all 14 PASS, no FAIL) |
| **Round 2** (Phase 8) | DEFERRED | §24.4 defines pass conditions (fixes reviewed, no regressions, criteria still pass); evidence directory `round-2/` exists |

---

## Secret Safety Verification

| Check | Result |
|---|---|
| Grep for actual bot token values (20+ char alphanumeric assigned to token vars) | **0 matches** |
| Grep for actual API key values | **0 matches** |
| Grep for actual DB password values | **0 matches** |
| All secret references use placeholders | **Yes** — `<SOPS>`, `<TOKEN>`, `<G>`, `<P>`, env var names |
| §2.5 explicitly forbids secret exposure | **Yes** — L230 |
| §1.5 BLOCKING rule forbids secret exposure | **Yes** — L146 |

---

## Recommendations

**None.** All 20 criteria pass. No recommendations needed.

Minor observations (non-blocking):

1. The plan references Discord guild ID `1_510_876_414_671_323_206` and channel ID `1_510_914_600_777_023_659` (§17.2, L3593-3594). These are infrastructure identifiers (not secrets) and are already present in the existing codebase. No action needed.
2. Round-1 audit reports 13 and 14 are in progress. This does not affect the hard rejection criteria audit — this report IS auditor 14.

---

## Footer

| Field | Value |
|---|---|
| **Auditor** | 14 (Hard Rejection Criteria) |
| **Verdict** | PASS |
| **Date** | 2026-06-28 |
| **Files Reviewed** | `p27-hermes-society-foundation-plan.md` (4779 lines), `p28-dual-autonomous-hermes-blueprint.md` (2921 lines), `p27-p28-p36-master-roadmap.md` (1245 lines), 11 research files, 10 existing audit reports |
| **Criteria Count** | 20/20 PASS |
| **Blocking Findings** | 0 |
| **Non-Blocking Observations** | 2 (see Recommendations) |
