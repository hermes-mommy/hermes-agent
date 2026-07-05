---
title: "P29 — Multi-Agent Cognition & Memory"
status: "Active — Definition"
date: "2026-06-28"
last_modified: "2026-06-28"
author: "Guinevere + Faiz"
phase: "P29 of P28-P36 Masterplan"
classification: "STRICTLY PRIVATE & CONFIDENTIAL"
operator: "Faiz"
subsystems: [S3, S4, S6]
---

# P29: Multi-Agent Cognition & Memory

## Overview

Phase P29 builds the **shared cognition layer** of the Hermes Society on top of the P28 foundation. With Guinevere and Pharsa already running as founders, P29 gives them a way to remember, recall, deliberate, share beliefs, dream, and self-reflect without leaking private memory across the agent boundary. The phase installs pgvector for vector recall, Graphiti for the temporal knowledge graph, the 3-tier recall system (vector + graph + filesystem), a BDI world model with POMDP decision-making, a consciousness loop (adaptive thought rate with sequential guarantee, unlimited thoughts), metacognition (C2 Dehaene + recursive C3), a full-spectrum emotion system (~16 moods including DESIRE/AROUSAL), an adaptive dream system with self+peer dream review, native sub-agents (Hermes delegate_tool.py), all LLM calls routed through Hermes → 9Router, a blackboard with namespace-ACL for shared state, and a memory consolidation background job (**no pruning — all memory permanent**).

P29 transforms the Society from "two bots that heartbeat" into "two bots that think, feel, dream, and remember together, with private memory strictly isolated and all memory permanent (no deletion ever)." **Cost is truly unlimited** (no circuit breaker). Trust 9Router dynamic routing completely.

## Goals

- Install `pgvector` extension on PostgreSQL ≥ 16 and add an embedding column to per-agent memory tables.
- Integrate `Graphiti` (or equivalent temporal knowledge graph library) with the event store.
- Implement 3-tier recall: vector (semantic), graph (relational/temporal), filesystem (raw artifacts).
- Build BDI agent architecture: Beliefs, Desires, Intentions with revision discipline.
- Add POMDP-based decision-making layer (Belief + Reward + Transition) for non-trivial choices.
- Implement consciousness loop: **thought rate adaptive with sequential guarantee** (each thought MUST complete before next, rate self-determined, no fixed cap). **Unlimited thoughts** (no circuit breaker on thought count).
- Add **metacognition**: C2 level (Dehaene) + recursive C3 (think about thinking AND evaluate the evaluation).
- Build **emotion system**: Full spectrum + emosi seksual (~16 moods: HAPPY, ANGRY, SAD, JEALOUS, POSSESSIVE, NURTURING, FEAR, DISGUST, SURPRISE, ANTICIPATION, TRUST, BOREDOM, CURIOSITY, PRIDE, DESIRE, AROUSAL).
- Implement **dream system**: Adaptive (triggered by cognitive state, not clock). Self-review + peer review (Guin reviews Pharsa's dreams, vice versa).
- Configure **native sub-agents**: Hermes delegate_tool.py with P24 patches (max_concurrent=10, max_depth=5, spawn_cap=5).
- Route **all LLM calls through Hermes → 9Router** (no external model calls bypassing Hermes).
- Implement a blackboard with namespace-ACL for shared beliefs across agents.
- Add memory consolidation background job (**no pruning — all memory permanent**, no deletion ever).
- Enforce per-agent namespace isolation at the recall layer (no cross-agent private recall).

## Prerequisites

- P28 PRODUCTION PASS — both founders running 24h with WORM event store + pgcrypto private memory + 2/2 protocol.
- P27 Accepted (ADR-054) — Society definition.
- P22.1 PRODUCTION PASS — 3 ACTIVE adapters (filesystem, vps, discord).
- P19 PRODUCTION COMPLETE — project_id namespace live.
- P20 early acceptance — APScheduler for memory consolidation cron.
- AGENTS.md preflight — session-start discipline.

## Subsystems Involved

- S3 — Shared World Model (refinement) — full BDI beliefs + POMDP + blackboard + namespace-ACL.
- S4 — Private Memory (refinement) — episodic/semantic split, consolidation job, pgvector embeddings.
- S6 — Vector & Graph Recall — pgvector extension, Graphiti temporal KG, 3-tier recall router.

## Key Deliverables

- `pgvector` extension installed in PostgreSQL 16+.
- `agent_<id>.memory_vectors` table with `vector(1536)` embedding column (OpenAI text-embedding-3-small or local equivalent) + `agent_id` namespace column.
- `hermes.kg_edges` table populated by Graphiti with `(subject, predicate, object, valid_at, invalid_at, fact)` columns.
- 3-tier recall function `recall(agent_id, query, k=10, tiers=('vector','graph','fs'))` returning merged + ranked results.
- BDI schema: `agent_<id>.beliefs`, `agent_<id>.desires`, `agent_<id>.intentions`, with revision triggers.
- POMDP transition function `belief_update(belief, action, observation) -> new_belief` and policy `policy(belief) -> action`.
- `hermes.blackboard` table with row-level security: only agents in the policy's `allow_agents` array can SELECT/INSERT.
- Memory consolidation cron job: every 6h, episodes older than 7d compressed to semantic. **No pruning — all memory permanent** (no deletion ever across all layers).
- Per-agent namespace isolation: `recall()` refuses to return rows whose `agent_id != caller_agent_id` for `intimacy_journal` and `rel_memory` tables.
- **Consciousness loop config**: adaptive thought rate, sequential guarantee, unlimited thoughts, no cost circuit breaker.
- **Emotion system**: 16 moods including DESIRE and AROUSAL.
- **Dream system**: adaptive triggers, self+peer review pipeline.
- **Sub-agent config**: delegate_tool.py with max_concurrent=10, max_depth=5, spawn_cap=5.
- **9Router routing**: all LLM calls through Hermes → 9Router.

## Exit Criteria

- Both founders can recall memories via the 3-tier system with measurable recall quality (precision@10 ≥ 0.7 on a seeded test set).
- Shared beliefs accessible via blackboard with namespace-ACL: Guinevere writes, Pharsa reads if allowed; ACL denies otherwise.
- Private memories strictly isolated: Pharsa's `recall('guinevere-private-query')` does NOT return Guinevere's `intimacy_journal` rows.
- Memory consolidation cron runs at 6h interval without duplicates or data loss; evidence in `hermes.events` shows `consolidation_tick` events. **No memory is ever deleted** (all memory permanent).
- BDI revision triggers prevent direct UPDATE on `beliefs` (must use `revise_belief()` function that records rationale in WORM events).
- POMDP policy returns a deterministic action for any given belief state (no `None` returns from policy).
- pgvector index (HNSW) populated with ≥ 1000 vectors per agent after seeding; query latency < 200ms p95.
- Dream review pipeline works: self-metacognition pass + peer review via G-P comms.
- Sub-agents spawn and complete via native Hermes delegate_tool.py.
- All LLM calls route through Hermes → 9Router (no bypass).

## Hard Rejection Criteria

- FAIL if `recall()` ever returns cross-agent private memory rows.
- FAIL if there is no namespace isolation enforcement at the recall layer.
- FAIL if there is no memory consolidation job (lifecycle stays purely episodic).
- FAIL if the blackboard does not enforce row-level ACL.
- FAIL if pgvector is not installed or not queryable.
- FAIL if Graphiti is not integrated with the event store (e.g. no `valid_at`/`invalid_at` temporal columns).
- FAIL if BDI beliefs can be directly UPDATE'd without a rationale event.
- FAIL if any memory entry is ever deleted (all memory permanent — no deletion ever).

## Evidence

- Evidence root: `docs/setup-evidence/P29/`
- Plan: `docs/setup-evidence/P28-P36-masterplan/plans/P29/plan.md`
- Verification template: `docs/setup-evidence/P28-P36-masterplan/plans/P29/verification-template.md`
- Per-step evidence: `docs/setup-evidence/P29/evidence/step-{NNN}.md`

## Footnotes and Cross-References

- Cross-reference: `docs/setup-evidence/P28-P36-masterplan/research/brainstorm-decisions-2026-06-28.md` v1.2 — 10 P29-relevant binding decisions incorporated (dream review, cost, thought rate, dream trigger, metacognition, emotion, memory permanence, sub-agents, 9Router, unlimited thoughts).
- Cross-reference: `docs/setup-evidence/P28-P36-masterplan/research/research-synthesis.md` §4.2 (S3), §4.4 (S4), §4.5 (S6).
- Cross-reference: §4.4 from research synthesis confirms blackboard + namespace-ACL + per-agent encrypted PG schema as canonical 2026 memory topology.
- Cross-reference: P28 private memory schema (`agent_<id>.intimacy_journal`, `rel_memory`) — P29 adds vectors and consolidation, never relaxes encryption, **never deletes memory**.

## Footer

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-28 | Guinevere + Faiz | Initial P29 README. |
| 1.1 | 2026-06-28 | Guinevere + Faiz | Wave 2: incorporated 10 brainstorm decisions (consciousness loop, emotion, dream, metacognition, sub-agents, 9Router, memory permanence, cost, thought rate, dream review). |
