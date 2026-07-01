---
title: "P29 Verification Template — Multi-Agent Cognition & Memory"
status: "Template — per-step verification scaffold"
date: "2026-06-28"
last_modified: "2026-06-28"
author: "Guinevere + Faiz"
phase: "P29 of P28-P36 Masterplan"
classification: "STRICTLY PRIVATE & CONFIDENTIAL"
operator: "Faiz"
---

# P29 Verification Template — Multi-Agent Cognition & Memory

## Verification Scaffold

| Step | Expected Files | Forbidden Patterns | Required Commands | Evidence Path | Hard Rejection |
|---|---|---|---|---|---|
| P29-001 | infra/db/12-14-*.sql | non-namespaced vectors; plaintext intimacy column | `\dx` shows `vector`; `\d agent_<id>.memory_vectors` shows `embedding vector(1536)` + `agent_id TEXT NOT NULL`; `EXPLAIN ANALYZE` uses HNSW | docs/setup-evidence/P29/evidence/step-001.md | FAIL if pgvector not installed; FAIL if HNSW unused |
| P29-002 | src/hermes/cognition/kg*.py; infra/db/15-kg-schema.sql; tests/test_kg.py | facts without source_event_id; bypassing event_store | `pytest test_kg.py` exit 0; `kg_edges` table has `(valid_at TIMESTAMPTZ, invalid_at TIMESTAMPTZ)`; `kg.add_fact(...)` from python creates a row | docs/setup-evidence/P29/evidence/step-002.md | FAIL if temporal columns missing; FAIL if tests fail |
| P29-003 | src/hermes/cognition/recall.py; rrf.py; tests/test_recall.py | cross-agent rows returned; non-RRF merge | `pytest test_recall.py` exit 0; `recall('pharsa', 'guinevere-private-query')` returns 0 from `intimacy_journal`; `RRF` used in merge | docs/setup-evidence/P29/evidence/step-003.md | FAIL if RRF not used; FAIL if cross-agent leak |
| P29-004 | infra/db/16-17-*.sql; src/hermes/cognition/bdi.py; tests/test_bdi.py | direct `UPDATE beliefs`; silent triggers | `UPDATE agent_<id>.beliefs SET content='x'` returns permission-denied trigger error; `revise_belief()` inserts event | docs/setup-evidence/P29/evidence/step-004.md | FAIL if direct UPDATE succeeds; FAIL if rationale NULL |
| P29-005 | src/hermes/cognition/pomdp.py; policy.py; tests/test_pomdp.py | policy returns `None`; ignoring observation | `pytest test_pomdp.py` exit 0; `policy(belief_x)` returns valid action; `decide()` < 200ms p95 | docs/setup-evidence/P29/evidence/step-005.md | FAIL if policy None; FAIL if decide > 200ms |
| P29-006 | infra/db/18-blackboard.sql; src/hermes/cognition/blackboard.py; tests/test_blackboard.py | RLS disabled; default allow-all; using `current_user` | `SELECT relrowsecurity FROM pg_class WHERE relname='blackboard'` = `t`; cross-actor SELECT returns 0 rows; proposer cannot read allow_agents that excludes them | docs/setup-evidence/P29/evidence/step-006.md | FAIL if RLS off; FAIL if default allow; FAIL if proposer overrides ACL |
| P29-007 | src/hermes/cognition/consolidation.py; src/hermes/cron/consolidation_cron.py; tests/test_consolidation.py | silent prune; no audit event | `pytest test_consolidation.py` exit 0; `consolidation.tick('guinevere')` emits `consolidation_tick` event; negative prune test emits `consolidation_prune`; idempotent (re-run on already-consolidated data = 0 events) | docs/setup-evidence/P29/evidence/step-007.md | FAIL if prune silent; FAIL if not idempotent |
| P29-008 | src/hermes/cognition/recall_authorizer.py; tests/test_namespace_isolation.py | logging blocked content; logging query verbatim | `pytest test_namespace_isolation.py` exit 0; `recall('pharsa', 'guinevere-private-keyword')` returns 0 intimacy rows; emits `cross_agent_blocked` event with count only | docs/setup-evidence/P29/evidence/step-008.md | FAIL if leak; FAIL if blocked event has content; FAIL if authorizer bypass |
| P29-009 | src/hermes/audit/cognition_tracer.py | silent `except:` around tracer; missing tracer call sites | `pytest test_audit_tracer.py` exit 0; `SELECT COUNT(*) FROM hermes.events WHERE event_type IN ('recall','belief_revision','blackboard_write','consolidation_tick')` non-zero after 5-min workload; `actor_agent_id` NOT NULL on all | docs/setup-evidence/P29/evidence/step-009.md | FAIL if tracer missing; FAIL if actor_agent_id NULL |
| P29-010 | tests/bench/recall_quality.py; docs/setup-evidence/P29/evidence/soak-24h-recall-report.md | skipping negative test; over-tuning benchmark | `python tests/bench/recall_quality.py` reports `precision_at_10 ≥ 0.7`; after 24h soak: both services active; `consolidation_tick` count exactly = 4 (every 6h); journalctl `ERROR` < 5; RestartCount < 3 each | docs/setup-evidence/P29/evidence/step-010.md (and recall_quality_report.md) | FAIL if precision < 0.7; FAIL if consolidation off-by-one; FAIL if restart > 3 |

## Binary Pass/Fail Criteria

1. pgvector extension installed (`\dx vector` returns 1 row) — PASS/FAIL
2. `agent_<id>.memory_vectors` exists with `embedding vector(1536)` + `agent_id TEXT NOT NULL` — PASS/FAIL
3. HNSW index created and used in query plan — PASS/FAIL
4. Graphiti integration populates `hermes.kg_edges` with `(valid_at, invalid_at)` — PASS/FAIL
5. 3-tier recall router returns merged RRF-ranked results — PASS/FAIL
6. Cross-agent negative recall test: `recall('pharsa', 'guinevere-private')` returns 0 intimacy rows — PASS/FAIL
7. Cross-agent negative recall test: rows return empty FOR VECTORS too — PASS/FAIL
8. BDI direct UPDATE blocked with rationale enforced — PASS/FAIL
9. POMDP policy returns valid action for every belief state (no `None`) — PASS/FAIL
10. POMDP `decide()` p95 latency < 200ms — PASS/FAIL
11. Blackboard RLS enabled (`relrowsecurity = t`) — PASS/FAIL
12. Blackboard cross-actor SELECT returns 0 rows when actor not in `allow_agents` — PASS/FAIL (negative test)
13. Memory consolidation cron tick emits `consolidation_tick` event with count — PASS/FAIL
14. Memory consolidation prune emits `consolidation_prune` event per prune — PASS/FAIL
15. Memory consolidation is idempotent (re-tick on consolidated = 0 events) — PASS/FAIL
16. Recall authorizer blocks cross-agent content rows at the query layer — PASS/FAIL
17. Cross-agent blocked events contain count only, no query content — PASS/FAIL
18. All cognition events have `actor_agent_id` NOT NULL in `hermes.events` — PASS/FAIL
19. Both founders run 24h soak active — PASS/FAIL
20. `consolidation_tick` event count = 4 in 24h window (every 6h) — PASS/FAIL
21. Recall precision@10 ≥ 0.7 on labeled query set — PASS/FAIL
22. RestartCount < 3 per agent over 24h — PASS/FAIL
23. journalctl `ERROR` lines < 5 over 24h — PASS/FAIL

## Runtime Proof Requirements

- `psql -c "EXPLAIN ANALYZE SELECT ... FROM agent_guinevere.memory_vectors ORDER BY embedding <=> '[...]' LIMIT 10"` — first plan node is `Index Scan using memory_vectors_embedding_idx` (HNSW).
- `python -c "from hermes.cognition.recall import recall; print(recall('pharsa', 'guinevere-private-keyword-test'))"` returns `[]` for intimacy rows (empty list).
- `python -m pytest tests/test_namespace_isolation.py -v` shows negative test PASS marked `cross_agent_blocked_event_emitted = True`.
- `python -c "from hermes.cognition.blackboard import write; write('guinevere', ['pharsa'], {...})"` succeeds as guinevere setting allow=['pharsa']; then `read('pharsa')` returns the row, `read('guinevere')` returns the row; then a third actor `read('third')` returns 0 rows.
- `psql -c "SELECT relrowsecurity FROM pg_class WHERE relname='blackboard'"` returns `t`.
- `python -c "from hermes.cognition.policy import policy; print(policy({'rap': 'Y4', 'energy': 'high'}))"` returns one of `'heartbeat', 'recall', 'revise', 'respond', 'idle'`, never `None`.
- `python tests/bench/recall_quality.py` stdout ends with `precision_at_10 = X.XX | PASS` (X.XX ≥ 0.7).
- After 24h soak: `SELECT COUNT(*) FROM hermes.events WHERE event_type='consolidation_tick' AND occurred_at > NOW() - INTERVAL '24 hours'` = 4.

## Parent Verification Checklist

- [ ] Claimed files exist (`ls src/hermes/cognition/*.py tests/test_*.py infra/db/[12-18]*.sql` all present)
- [ ] Changed files parent-read (parent cross-checks ≥ 30% of new file bodies against plan §4)
- [ ] `lsp_diagnostics` clean on all new/changed Python files
- [ ] Tests pass for each step (`pytest tests/test_<step>.py -v`)
- [ ] Recall benchmark passes (`precision_at_10 ≥ 0.7`)
- [ ] Evidence paths exist (`docs/setup-evidence/P29/evidence/step-{NNN}.md` for all 10 steps)
- [ ] Auditor reports exist (`docs/setup-evidence/P29/evidence/audits/step-{NNN}-audit.md` for all 10 steps)
- [ ] Safety boundaries preserved (no pgcrypto relaxation on intimacy_journal; no Y5 escalation; no HARD STOP bypass)
- [ ] No type suppression (`grep -rn "as any\|# type: ignore\|@ts-ignore" src/hermes/cognition/` returns empty)
- [ ] No empty catches around tracer (`grep -rn "except:\|except Exception:" src/hermes/audit/ src/hermes/cognition/` returns no silent pattern)
- [ ] Soak report prepared with consolidation tick count, restart count, journalctl error count
- [ ] Cross-agent negative tests captured in evidence (intimacy AND vectors)

## Footer

Version 1.0 | Date: 2026-06-28 | Author: Guinevere + Faiz
