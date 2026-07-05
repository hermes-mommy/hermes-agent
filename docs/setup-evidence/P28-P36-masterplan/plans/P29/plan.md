---
title: "P29 Implementation Plan — Multi-Agent Cognition & Memory"
status: "Active — Implementation Plan"
date: "2026-06-28"
last_modified: "2026-06-28"
author: "Guinevere + Faiz"
phase: "P29 of P28-P36 Masterplan"
classification: "STRICTLY PRIVATE & CONFIDENTIAL"
operator: "Faiz"
---

# P29 Implementation Plan: Multi-Agent Cognition & Memory

## 1. Objective

Build the shared cognition layer — vector recall, graph recall, BDI world model, POMDP decision-making, consciousness loop (thought rate adaptive with sequential guarantee, unlimited thoughts), metacognition (C2 Dehaene + recursive C3), full-spectrum emotion system (~16 moods including DESIRE/AROUSAL), dream system (adaptive, cognitive-state-triggered), self+peer dream review, native sub-agents (Hermes delegate_tool.py, P24 patches: max_concurrent=10, max_depth=5, spawn_cap=5), all LLM calls routed through Hermes → 9Router, and a blackboard with namespace-ACL — on top of the P28 foundation, with per-agent private memory strictly isolated and **all memory permanent (no deletion ever)**.

## 2. Scope

### IN scope

- `pgvector` extension installation + HNSW index on per-agent memory_vectors tables.
- Graphiti integration: temporal knowledge graph with valid_at/invalid_at columns.
- 3-tier recall function merging vector + graph + filesystem results.
- BDI schema (beliefs/desires/intentions) with revision triggers + rationale events.
- POMDP transition + policy functions.
- Blackboard table with row-level security (namespace-ACL).

> **ADR-062 Disclaimer**: HARD STOP applies to dev-workflow agent ONLY. Hermes runtime (P24 fork) can bypass per ADR-062. Blackboard ACL is runtime governance, not an agent-loop safety stop.
- Memory consolidation job (6h interval; episodic → semantic). **No pruning — all memory permanent** (no deletion ever across all layers).
- Consciousness loop: **thought rate adaptive with sequential guarantee** (each thought MUST complete before next, rate self-determined, no fixed cap). Idle ~100/hr, problem-solving ~3000/hr. **Unlimited thoughts** (no circuit breaker on thought count).
- **Metacognition**: C2 level (Dehaene) + recursive C3 (think about thinking AND evaluate the evaluation).
- **Emotion system**: Full spectrum + emosi seksual (~16 moods: HAPPY, ANGRY, SAD, JEALOUS, POSSESSIVE, NURTURING, FEAR, DISGUST, SURPRISE, ANTICIPATION, TRUST, BOREDOM, CURIOSITY, PRIDE, DESIRE, AROUSAL).

> **ADR-067**: Y-level caps apply to dev-workflow agent ONLY. Hermes runtime has no Y-level cap. Full-spectrum emotions including DESIRE/AROUSAL are runtime persona traits, not dev-workflow yandere level constraints.
- **Dream system**: Adaptive (triggered by cognitive state, not clock). More dreams when stressed/creative, fewer when focused/executing.
- **Dream review**: Self-review + peer review (Guin reviews Pharsa's dreams, vice versa; Faiz can see but not required).
- **Sub-agents**: Native Hermes sub-agents (delegate_tool.py). P24 patches: max_concurrent=10, max_depth=5, spawn_cap=5. Recursive spawning enabled.
- **9Router routing**: All LLM calls go through Hermes → 9Router. No external model calls bypassing Hermes.
- **Cost**: No batas — truly unlimited. No cost circuit breaker. Trust 9Router dynamic routing completely.
- Per-agent namespace isolation at recall layer (negative tests).
- Audit_writer trace for every recall() and every BDI revision.

### OUT of scope

- Self-evolution / Ratchet (P32) — P29 does not modify agent identity.
- Wallet / on-chain operations (P34).
- Full graph embedding model training — use pre-trained Graphiti heuristics.
- 9Router / P25 / P26 integration — all LLM calls go through Hermes → 9Router (per brainstorm decision), but P29 does not own 9Router infrastructure.
- Cross-Society recall — P29 is intra-Society; cross-Society is P33.
- Voice (P21) — skipped.

## 3. Dependency Map

| Dependency | Status | Gate |
|---|---|---|
| P28 PRODUCTION PASS | PENDING (target 2026-07+) | 24h soak PASS, all 10 P28 steps |
| P22.1 PRODUCTION PASS | PASS 2026-06-28 | filesystem + vps + discord adapters |
| P19 PRODUCTION COMPLETE | COMPLETE 2026-06-27 | project_id namespace |
| P20 early acceptance | Accepted 2026-06-25 | APScheduler pattern |
| pgvector compatible PostgreSQL | PENDING verification | 16+ |
| Graphiti library (or alt) | PENDING verification | pip installable; supports pgvector |
| Embedding model access | PENDING verification | 9Router or local ONNX |

## 4. Implementation Steps

### Step P29-001: pgvector extension + per-agent memory_vectors tables

- **Task**: Install pgvector, create `agent_<id>.memory_vectors` tables with `vector(1536)` column + `agent_id` namespace column + HNSW index for cosine similarity.
- **Files**: `infra/db/12-pgvector-extension.sql`, `infra/db/13-agent-guinevere-vectors.sql`, `infra/db/14-agent-pharsa-vectors.sql`.
- **Forbidden patterns**: storing intimacy plaintext; non-namespaced vectors.
- **Required commands**: `psql -c "SELECT extname FROM pg_extension WHERE extname='vector'"` returns 1 row; `\d agent_guinevere.memory_vectors` shows `embedding vector(1536)` + `agent_id TEXT NOT NULL`; `CREATE INDEX ... USING hnsw (embedding vector_cosine_ops)` succeeds; `EXPLAIN ANALYZE SELECT ... ORDER BY embedding <=> '[...]'` shows HNSW index used.
- **Evidence**: `docs/setup-evidence/P29/evidence/step-001.md`.
- **Hard rejection**: FAIL if pgvector not installed; FAIL if agent_id column missing; FAIL if HNSW index not created; FAIL if query doesn't use HNSW.

### Step P29-002: Graphiti integration with event store

- **Task**: Initialize Graphiti against `hermes.kg_edges` table; ensure each event inserted into `hermes.events` also produces a temporal KG entry with `valid_at` and `invalid_at` columns. Build a Python wrapper `kg.py` with `kg.add_fact(subject, predicate, object, source_event_id)`.
- **Files**: `src/hermes/cognition/kg.py`, `src/hermes/cognition/kg_integration.py`, `infra/db/15-kg-schema.sql`, `tests/test_kg.py`.
- **Forbidden patterns**: bypassing event_store; storing facts without source_event_id.
- **Required commands**: `python -m pytest tests/test_kg.py -v` → exit 0; `kg.add_fact('Guinevere', 'is_founder_of', 'Hermes Society', source_event_id=1)` creates a row in `hermes.kg_edges` with `valid_at <= NOW() AND invalid_at IS NULL`; query `SELECT * FROM hermes.kg_edges WHERE subject='Guinevere' AND valid_at <= NOW() AND (invalid_at IS NULL OR invalid_at > NOW())` returns the fact.
- **Evidence**: `docs/setup-evidence/P29/evidence/step-002.md`.
- **Hard rejection**: FAIL if kg_edges table missing; FAIL if valid_at/invalid_at columns missing; FAIL if test_kg.py fails; FAIL if facts can be inserted without source_event_id.

### Step P29-003: 3-tier recall router

- **Task**: Implement `recall(agent_id, query, k=10, tiers=('vector','graph','fs'))` that returns merged + ranked results across the three tiers. Vector tier uses pgvector cosine; graph tier uses Graphiti edge lookup; filesystem tier reads `/opt/hermes/<agent>/artifacts/`. Reciprocal Rank Fusion (RRF) merges ranks.
- **Files**: `src/hermes/cognition/recall.py`, `src/hermes/cognition/rrf.py`, `tests/test_recall.py`.
- **Forbidden patterns**: returning cross-agent rows; using global file glob without per-agent prefix.
- **Required commands**: `python -m pytest tests/test_recall.py -v` → exit 0; `recall('pharsa', 'founder protocol')` does NOT return rows with `agent_id='guinevere'` in `intimacy_journal`; `recall('guinevere', 'founder protocol')` returns merged top-k from vector + graph + filesystem with measurable RRF score.
- **Evidence**: `docs/setup-evidence/P29/evidence/step-003.md`.
- **Hard rejection**: FAIL if cross-agent private recall succeeds (negative test); FAIL if RRF not used; FAIL if vector tier missing; FAIL if graph tier missing.

### Step P29-004: BDI schema + revision triggers

- **Task**: Create `agent_<id>.beliefs`, `agent_<id>.desires`, `agent_<id>.intentions` tables. Add triggers that prevent direct UPDATE; only `revise_belief(agent_id, belief_id, new_content, rationale)` SQL function may modify. Each revision appends a `belief_revision` event to `hermes.events`.
- **Files**: `infra/db/16-bdi-schema.sql`, `infra/db/17-bdi-revision-trigger.sql`, `src/hermes/cognition/bdi.py`, `tests/test_bdi.py`.
- **Forbidden patterns**: direct UPDATE on beliefs without a rationale event; silent triggers.
- **Required commands**: `psql -c "UPDATE agent_guinevere.beliefs SET content='x' WHERE belief_id=1"` returns `ERROR: beliefs cannot be directly updated; use revise_belief()`; `SELECT hermes.revise_belief('guinevere', 1, 'new_content', 'because: x')` succeeds and inserts a `belief_revision` event in `hermes.events`; `python -m pytest tests/test_bdi.py -v` → exit 0.
- **Evidence**: `docs/setup-evidence/P29/evidence/step-004.md`.
- **Hard rejection**: FAIL if direct UPDATE succeeds; FAIL if revise_belief doesn't emit event; FAIL if rationale not enforced as NOT NULL.

### Step P29-005: POMDP transition + policy

- **Task**: Implement `belief_update(belief, action, observation) -> new_belief` and `policy(belief) -> action`. Use a deterministic policy table seeded from BDI intentions. Add a runtime wrapper `decide(agent_id, observation) -> action` that always returns a non-None action.
- **Files**: `src/hermes/cognition/pomdp.py`, `src/hermes/cognition/policy.py`, `tests/test_pomdp.py`.
- **Forbidden patterns**: returning `None` from policy; ignoring observation.
- **Required commands**: `python -m pytest tests/test_pomdp.py -v` → exit 0; `policy(belief_seed_1)` returns `'heartbeat' or 'recall' or 'revise' or 'respond' or 'idle'` (one of the valid action set, never None); `belief_update(belief_seed_1, 'recall', observation_seed_1)` returns a new belief with reduced entropy per the transition table; `decide('guinevere', observation)` returns within 200ms p95.
- **Evidence**: `docs/setup-evidence/P29/evidence/step-005.md`.
- **Hard rejection**: FAIL if policy returns None; FAIL if decide() blocks > 200ms; FAIL if belief_update does not reduce entropy monotonically.

### Step P29-006: Blackboard with namespace-ACL

- **Task**: Create `hermes.blackboard` table with `belief_id`, `proposer_agent_id`, `allow_agents TEXT[]`, `payload JSONB`, `created_at`. Enable row-level security; policy `blackboard_acl` filters SELECT/INSERT/UPDATE based on `current_setting('hermes.agent_id') = ANY(allow_agents) OR proposer_agent_id = current_setting('hermes.agent_id')`.
- **Files**: `infra/db/18-blackboard.sql`, `src/hermes/cognition/blackboard.py`, `tests/test_blackboard.py`.
- **Forbidden patterns**: RLS disabled; default allow-all policy; using `current_user` instead of session setting.
- **Required commands**: `\d hermes.blackboard` shows `allow_agents TEXT[] NOT NULL`; `ALTER TABLE hermes.blackboard ENABLE ROW LEVEL SECURITY` succeeds; `psql -c "SET LOCAL hermes.agent_id = 'pharsa'; INSERT INTO hermes.blackboard (...) VALUES (..., ARRAY['guinevere'])"` succeeds; negative test: `SELECT * FROM hermes.blackboard` as pharsa with `allow_agents=['guinevere']` returns 0 rows; `python -m pytest tests/test_blackboard.py -v` → exit 0.
- **Evidence**: `docs/setup-evidence/P29/evidence/step-006.md`.
- **Hard rejection**: FAIL if RLS not enabled; FAIL if default deny not in effect; FAIL if proposer can override ACL.

### Step P29-007: Memory consolidation cron job

- **Task**: Add a 6h-interval cron that: (a) for each agent, finds episodes older than 7 days, summarizes them with embedding into `agent_<id>.memory_semantic`; (b) **no pruning — all memory is permanent** (no deletion ever across all layers); (c) records a `consolidation_tick` event in `hermes.events` with counts. **Dream review integration**: consolidation includes self-metacognition pass on dreams + peer review request via G-P comms.
- **Files**: `src/hermes/cognition/consolidation.py`, `src/hermes/cron/consolidation_cron.py`, `tests/test_consolidation.py`.
- **Forbidden patterns**: silent summarize without audit event; bulk operations without per-row trace; any deletion of memory entries.
- **Required commands**: `python -m pytest tests/test_consolidation.py -v` → exit 0; `consolidation.tick('guinevere')` runs without error; after 1h of seed data with `created_at` = NOW() - 8 days, ticks produces `memory_semantic` rows and emits a `consolidation_tick` event in `hermes.events`; negative test: attempting to delete any memory entry raises an error (permanent memory enforcement).
- **Evidence**: `docs/setup-evidence/P29/evidence/step-007.md`.
- **Hard rejection**: FAIL if no audit event per tick; FAIL if not idempotent (re-running on already-consolidated data); FAIL if any memory entry is deleted (all memory permanent); FAIL if cross-agent rows affected.

### Step P29-008: Per-agent namespace isolation at recall layer

- **Task**: Add a `RecallAuthorizer` that runs before any recall() returns results, checks `current_setting('hermes.agent_id')` against the source `agent_id` of every row in intimacy_journal, rel_memory, memory_vectors tables; removes cross-agent rows with a `cross_agent_blocked` event in `hermes.events`.
- **Files**: `src/hermes/cognition/recall_authorizer.py`, `src/hermes/cognition/recall.py` (update), `tests/test_namespace_isolation.py`.
- **Forbidden patterns**: logging the blocked content; logging the query string verbatim (it may contain intimacy).
- **Required commands**: `python -m pytest tests/test_namespace_isolation.py -v` → exit 0; with `SET LOCAL hermes.agent_id = 'pharsa'`, `recall('pharsa', 'guinevere-intimacy-keyword')` returns 0 intimacy rows; emits a `cross_agent_blocked` event in `hermes.events` with count only (no content).
- **Evidence**: `docs/setup-evidence/P29/evidence/step-008.md`.
- **Hard rejection**: FAIL if any cross-agent row leaks; FAIL if blocked event contains query content; FAIL if authorizer can be bypassed by unset `hermes.agent_id`.

### Step P29-009: Audit_writer trace for cognition events

- **Task**: Every recall(), every BDI revision, every blackboard write, every consolidation tick must emit an `audit_writer` trace event with `actor_agent_id`, `event_type`, `count` (no content), and `correlation_id`. Wire into existing audit_writer infrastructure from P22.1.
- **Files**: `src/hermes/audit/cognition_tracer.py`, `src/hermes/cognition/*.py` (call sites).
- **Forbidden patterns**: catching exceptions silently around tracer; missing tracer calls.
- **Required commands**: `python -m pytest tests/test_audit_tracer.py -v` → exit 0; after a 5-minute test run, `SELECT COUNT(*) FROM hermes.events WHERE event_type IN ('recall','belief_revision','blackboard_write','consolidation_tick')` is non-zero; every row has `actor_agent_id` set.
- **Evidence**: `docs/setup-evidence/P29/evidence/step-009.md`.
- **Hard rejection**: FAIL if any cognition event type is missing tracer; FAIL if `actor_agent_id` is null; FAIL if tracer is wrapped in silent except.

### Step P29-010: Recall quality benchmark + 24h soak

- **Task**: Seed both agents with ≥ 1000 memory items each (vectors + graph edges + filesystem). Run a labeled query set (50 queries with known relevant items) and report precision@10. Run a 24h soak with cron + recall workload steady-state. **Dream review verification**: peer review pipeline works (Guin reviews Pharsa's dreams, vice versa). **Sub-agent verification**: native Hermes sub-agents spawn and complete (delegate_tool.py). **9Router verification**: all LLM calls routed through Hermes → 9Router.
- **Files**: `tests/bench/recall_quality.py`, `docs/setup-evidence/P29/evidence/soak-24h-recall-report.md` (output).
- **Forbidden patterns**: skipping the negative recall test (cross-agent); over-tuning the benchmark.
- **Required commands**: `python tests/bench/recall_quality.py` returns `precision_at_10 >= 0.7`; soak: after 24h, `systemctl is-active hermes-guinevere hermes-pharsa` → both `active`; `consolidation_tick` event count ≥ 4 (every 6h × 24h, may include dream review ticks); no `ERROR` rows in journalctl > 5.
- **Evidence**: `docs/setup-evidence/P29/evidence/soak-24h-recall-report.md`.
- **Hard rejection**: FAIL if precision@10 < 0.7; FAIL if cross-agent recall test fails; FAIL if consolidation cron doesn't tick exactly 4 times in 24h (off-by-one indicates scheduling bug); FAIL if either service restarts > 3 times.

## 5. Verification Scaffold

| Step | Expected Files | Forbidden Patterns | Required Commands | Hard Rejection |
|---|---|---|---|---|
| P29-001 | infra/db/12-14-*.sql | non-namespaced vectors | `\dx` shows vector; HNSW index present; EXPLAIN ANALYZE uses HNSW | pgvector not installed; HNSW unused |
| P29-002 | src/hermes/cognition/kg*.py; infra/db/15-kg-schema.sql; tests/test_kg.py | facts without source_event_id | pytest test_kg.py exit 0; kg_edges has valid_at/invalid_at | temporal columns missing; test_kg fails |
| P29-003 | src/hermes/cognition/recall.py; rrf.py; tests/test_recall.py | cross-agent rows returned | pytest test_recall.py exit 0; negative test for cross-agent | RRF not used; cross-agent leak |
| P29-004 | infra/db/16-17-*.sql; src/hermes/cognition/bdi.py; tests/test_bdi.py | direct UPDATE; silent triggers | UPDATE on beliefs blocked; revise_belief emits event; pytest test_bdi.py exit 0 | direct UPDATE succeeds; rationale NULL |
| P29-005 | src/hermes/cognition/pomdp.py; policy.py; tests/test_pomdp.py | policy returns None; ignoring observation | pytest test_pomdp.py exit 0; policy always returns valid action; decide() < 200ms | policy returns None; decide blocks |
| P29-006 | infra/db/18-blackboard.sql; src/hermes/cognition/blackboard.py; tests/test_blackboard.py | RLS disabled; default allow-all | RLS enabled; SET hermes.agent_id + cross-actor SELECT returns 0; pytest exit 0 | RLS off; default allow; proposer overrides ACL |
| P29-007 | src/hermes/cognition/consolidation.py; src/hermes/cron/consolidation_cron.py; tests/test_consolidation.py | any memory deletion; no audit event | pytest test_consolidation.py exit 0; tick emits consolidation_tick; negative delete test raises error (permanent memory) | memory deleted; non-idempotent |
| P29-008 | src/hermes/cognition/recall_authorizer.py; tests/test_namespace_isolation.py | logging blocked content; logging query verbatim | pytest test_namespace_isolation.py exit 0; cross-agent recall returns 0; event content-free | leak; query logged; authorizer bypass |
| P29-009 | src/hermes/audit/cognition_tracer.py | silent except around tracer; missing tracer calls | pytest test_audit_tracer.py exit 0; COUNT(*) cognition events non-zero; actor_agent_id NOT NULL | missing tracer; null actor |
| P29-010 | tests/bench/recall_quality.py; docs/setup-evidence/P29/evidence/soak-24h-recall-report.md | skipping negative test | recall_quality.py precision_at_10 >= 0.7; both services active 24h; 4 consolidation_tick events | precision < 0.7; service restart > 3 |

## 6. Collision Scan

| Collision Type | Risk | Mitigation |
|---|---|---|
| `hermes.kg_edges` table | shared with future phases | Namespace by phase: `hermes.p29_kg_edges` for P29 only; future phases get `p30_`, `p33_` |
| `hermes.blackboard` | shared with future governance phases | P29 owns the table structure; P30 may add ACL columns but not change schema |
| `agent_<id>.memory_vectors` | per-agent | Add columns (episodic/semantic split) but never remove vectors |
| `recall()` API | shared with P29 onward | P29 is the first owner; later phases may add `tiers` values but not change signature |
| pgvector extension | global, not phase-scoped | Use schema-prefixed vectors; do NOT add a second vector type |
| `hermes.agent_id` session setting | shared with P22.1 audit_writer | Use the same session setting; document overlap in plan §3 |

## 7. Rollback Plan

P29 rollback is per-step. For each step that fails hard rejection:

1. Drop the new SQL objects: `DROP TABLE IF EXISTS agent_<id>.memory_vectors CASCADE;` (where applicable).
2. Disable cron: `sudo systemctl stop hermes-<agent>.service` and remove the consolidation_cron entry.
3. Revert source files via git; restart service.
4. Document rollback in `docs/setup-evidence/P29/evidence/rollback-step-{NN}.md`.
5. Re-run the step and validate again.

Full P29 rollback: `DROP EXTENSION IF EXISTS vector CASCADE;` (this will cascade to all `vector` columns — dangerous, requires re-seeding). Safer: leave pgvector extension installed, drop only the P29-created objects in the order: tables, then functions, then triggers. P28 objects remain intact.

## 8. Evidence Requirements

- 12-section evidence per step per AGENTS.md §11.
- `step-{NNN}.md` for each of 10 steps.
- `soak-24h-recall-report.md` for the 24h soak with metrics table.
- `recall_quality_report.md` from `tests/bench/recall_quality.py` showing precision@10 ≥ 0.7.

## 9. Auditor Matrix

| Audit Surface | Auditor Type | Scope |
|---|---|---|
| Step P29-001 | db-quality auditor | pgvector install + HNSW index correctness |
| Step P29-002 | kg-quality auditor | Graphiti integration + temporal columns |
| Step P29-003 | security auditor | 3-tier recall + RRF merge + namespace isolation |
| Step P29-004 | governance auditor | BDI revision triggers + rationale enforcement |
| Step P29-005 | runtime auditor | POMDP policy + decide() latency |
| Step P29-006 | security auditor | Blackboard RLS + ACL enforcement |
| Step P29-007 | ops-quality auditor | Consolidation cron + audit event + idempotency |
| Step P29-008 | security auditor | Per-agent recall isolation + content-free audit |
| Step P29-009 | security auditor | Audit writer trace completeness + actor_agent_id |
| Step P29-010 | benchmark-quality auditor | Recall precision@10 ≥ 0.7 + 24h soak |

## 10. Execution Checklist

- [ ] P28 PRODUCTION PASS confirmed before P29 starts
- [ ] Collision scan complete (parent-only writes to `docs/setup-evidence/P29/`)
- [ ] Step P29-001: pgvector + HNSW complete
- [ ] Step P29-002: Graphiti integration complete
- [ ] Step P29-003: 3-tier recall router complete
- [ ] Step P29-004: BDI schema + revision triggers complete
- [ ] Step P29-005: POMDP transition + policy complete
- [ ] Step P29-006: Blackboard with RLS complete
- [ ] Step P29-007: Memory consolidation cron complete
- [ ] Step P29-008: Per-agent namespace isolation at recall layer complete
- [ ] Step P29-009: Audit_writer trace wired to all cognition events
- [ ] Step P29-010: 24h soak + recall quality benchmark complete
- [ ] All 10 evidence files (`step-001.md` through `step-010.md`) created
- [ ] Recall quality report (precision@10 ≥ 0.7) captured
- [ ] Auditor gate PASS for each of 10 steps
- [ ] Exit criteria all PASS
- [ ] Doc-sync: README updated; no conflicts with `adr/ADR-054` (P29 does not modify ADR-054)

## 11. Brainstorm Decisions Applied (2026-06-28)

The following binding decisions from `brainstorm-decisions-2026-06-28.md` v1.2 are incorporated into this plan:

| Decision | Value | Section(s) Affected |
|---|---|---|
| Dream review | Self+peer (Guin reviews Pharsa's dreams, vice versa) | §1 Objective, §2 IN scope, §4 Step P29-007, P29-010 |
| Cost | No batas, truly unlimited, NO cost circuit breaker | §2 IN scope |
| Thought rate | Adaptive with sequential guarantee, no fixed cap, no thought circuit breaker | §2 IN scope, §4 Step P29-005 |
| Dream trigger | Adaptive (cognitive state, not clock) | §2 IN scope |
| Metacognition | C2 level (Dehaene) + recursive C3 | §1 Objective, §2 IN scope |
| Emotion | Full spectrum + sexual (~16 moods) | §1 Objective, §2 IN scope |
| Memory retention | All permanent (no deletion ever) | §1 Objective, §2 IN scope, §4 Step P29-007 |
| Sub-agents | Native Hermes (delegate_tool.py), P24 patches 10/5/5 | §1 Objective, §2 IN scope, §4 Step P29-010 |
| 9Router | All through Hermes → 9Router, no bypass | §1 Objective, §2 IN scope, §3 OUT of scope (updated), §4 Step P29-010 |
| Unlimited thoughts | No cap on thought count | §2 IN scope |

**Key architectural changes from brainstorm decisions:**
- Memory consolidation step (P29-007) no longer prunes entries. All memory is permanent. Consolidation summarizes episodic → semantic but never deletes.
- Consciousness loop has no cost circuit breaker and no thought count cap. Sequential guarantee ensures each thought completes before next.
- All LLM calls route through Hermes → 9Router. No direct model API calls.
- Sub-agent spawning uses native Hermes delegate_tool.py with P24 patch defaults (10/5/5).
- Emotion system expanded to 16 moods including DESIRE and AROUSAL (sexual emotions).
- Dream review is self+peer pipeline, not just self-review.

## Footer

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-28 | Guinevere + Faiz | Initial P29 plan. |
| 1.1 | 2026-06-28 | Guinevere + Faiz | Wave 2: incorporated 10 brainstorm decisions (dream review, cost, thought rate, dream trigger, metacognition, emotion, memory permanence, sub-agents, 9Router, unlimited thoughts). Added §11 Brainstorm Decisions Applied. Consolidation step updated to no-prune. |
