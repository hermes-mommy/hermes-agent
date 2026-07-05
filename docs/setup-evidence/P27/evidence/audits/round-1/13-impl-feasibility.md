---
title: "P28 Implementation Feasibility Audit"
audit_id: "P27-R1-13"
date: "2026-06-28"
auditor: "Guinevere (sub-agent)"
scope: "P28 blueprint executability — can P28 be implemented from the plan + blueprint?"
target_file: "docs/setup-evidence/P27/plan/p28-dual-autonomous-hermes-blueprint.md"
plan_file: "docs/setup-evidence/P27/plan/p27-hermes-society-foundation-plan.md (§17-§18)"
research_file: "docs/setup-evidence/P27/research/p27-hermes-native-runtime-inventory.md"
status: "Complete"
---

# P28 Implementation Feasibility Audit

## VERDICT: NEEDS REVIEW

**Rationale:** The P28 blueprint is highly executable — 14 sections, 15 atomic steps with concrete goal/files/approach/verification/rollback, full SQL DDL, copy-pasteable Python, machine-checkable bash verification commands. However, 4 findings (2 HIGH, 2 MEDIUM) require resolution before implementation begins. None are blocking-by-nature (they can be fixed in-place); all are detectable by a careful developer.

---

## Findings

### F-01 [HIGH] Missing `src/core/society_app.py` creation step (phantom reference)

**Location:** Blueprint §3.5 Step 5 (L1010, L1030); §2.6 files-to-create list (L151-198)

**Issue:** Step 5's `pharsa-core.service` ExecStart references `src.core.society_app:app` (L1030):
```
ExecStart=.../.venv/bin/python -m uvicorn src.core.society_app:app --host 127.0.0.1 --port 20130
```

However, `src/core/society_app.py` is **not listed** in the files-to-create table (§2.6, L151-198), nor is it created in Step 3 (modifies `src/core/main.py`), Step 4 (creates `instance_registry.py`), or any other step.

Step 3 Sub-step 3D (L607-636) modifies `src/core/main.py` to create `app.state.hermes_brains` dict from `society_manifest.yaml`. This would load ALL instances in every process. For Pharsa's service on port 20130, this means:

- Option A: Pharsa's process loads both brains (wastes resources, but works — `society_app` not needed; use `src.core.main:app`).
- Option B: A new `src/core/society_app.py` is needed that loads only the instance specified by `PHARSA__CONFIG_PATH` env var.

The blueprint references Option B but never creates it. A developer following the plan literally will hit a `ModuleNotFoundError` at Step 5.

**Impact:** Blocks Step 5 systemd unit deployment. A developer can infer the fix (create `society_app.py` or change `ExecStart` to `src.core.main:app`), but the plan should be explicit.

**Recommendation:** Add `src/core/society_app.py` (~80 lines) to Step 3 or Step 4 files-to-create list, OR change Step 5's ExecStart to `src.core.main:app` and clarify that each process loads only its own instance via `PHARSA__CONFIG_PATH`/`GUINEVERE__CONFIG_PATH` env var.

---

### F-02 [HIGH] `memory.shared_world.retrievability` formula is buggy (`now() - now()` = 0)

**Location:** Blueprint §3.6 Step 6, Migration 003 (L1256-1259)

**Issue:** The `shared_world` table's `retrievability` GENERATED column formula is:
```sql
exp(-1.0 * ((extract(epoch from now()) - extract(epoch from now()))
        / NULLIF(stability::real * 86400, 0))) * importance_score
```

The second `now()` should be `last_accessed_at` (compare with the correct formula in Migration 002 for `private_agents` at L1201-1204, which uses `last_accessed_at`). As written, `now() - now() = 0`, so `exp(0) * importance_score = importance_score` — no time-decay occurs. This means shared-world facts never decay, contradicting the Ebbinghaus model described in the memory spec (§7) and P27 §6.2.3.

**Impact:** Data correctness bug. Shared world entries will appear permanently at maximum retrievability regardless of age or access patterns. If an implementer copies this DDL verbatim, the bug ships to production.

**Recommendation:** Fix L1257 to:
```sql
exp(-1.0 * ((extract(epoch from now()) - extract(epoch from last_accessed_at))
        / NULLIF(stability::real * 86400, 0))) * importance_score
```

---

### F-03 [MEDIUM] `hpp_outbox` and `hpp_inbox` table DDL not in any migration file

**Location:** Blueprint §2.4 (L134-135), §3.8 Step 8 (L1565-1647), §3.9 Step 9 (L1655-1699)

**Issue:** §2.4 PostgreSQL Requirements (L134-135) states:
- `New: hpp_outbox table | P28 creates | Step 8`
- `New: hpp_inbox table | P28 creates | Step 9`

§3.6 Step 6 creates 7 migration files (001-007) but none include `hpp_outbox` or `hpp_inbox` DDL. Step 8 (L1552-1647) mentions the outbox pattern but does not provide the `CREATE TABLE hpp_outbox` SQL. Step 9 (L1663-1665) mentions `hpp_inbox` with UNIQUE constraint but does not provide the `CREATE TABLE hpp_inbox` SQL.

The rollback commands (L1645-1646, L1698) reference `DROP TABLE IF EXISTS hpp_outbox` and `hpp_inbox`, confirming these tables are expected to exist.

**Impact:** An implementer must design these table schemas themselves, introducing inconsistency risk. The blueprint's explicit promise of machine-checkable steps is broken for these tables.

**Recommendation:** Add `migrations/p28/008_hpp_outbox.sql` and `migrations/p28/009_hpp_inbox.sql` to Step 8 and Step 9 respectively, with explicit DDL matching the outbox/inbox patterns described in the approach sections. At minimum, provide column schemas inline in Step 8/9.

---

### F-04 [MEDIUM] `_cascade_halt()` logs but does not halt instances

**Location:** Blueprint §3.4 Step 4 (L869-878)

**Issue:** The `HermesInstanceRegistry._cascade_halt()` method (L869-878) writes audit entries but does NOT call `stop_all()` or cancel any rail tasks:
```python
async def _cascade_halt(self) -> None:
    for instance in self._instances.values():
        try:
            await instance.audit_writer.write_hard_stop_state(
                society_key=SOCIETY_HARD_STOP_KEY,
            )
        except Exception as e:
            logger.exception(...)
```

Compare with `_watch_society_hard_stop()` (L853-867) which sets `self._is_halted = True` (stops the watcher) and calls `_cascade_halt()`. But `_cascade_halt` only writes audit rows — it does not:
1. Cancel MinimalScheduler tasks (rails keep ticking).
2. Flush thought buffers.
3. Flush peer messages (per `pharsa.yaml` config L449: `halt_rails: true, seal_thought_buffers: true, flush_peer_messages: true`).

The `stop_all(graceful=True)` method at L880-891 exists and DOES halt properly, but it is only called externally (e.g., on SIGTERM), not by `_cascade_halt`.

**Impact:** HARD STOP cascade will not actually halt the agents' life-loop rails within 50ms (acceptance criterion #10). The audit entries will be written, but agents continue processing. Test 2 (§10.5) would fail because rails are not stopped.

**Recommendation:** Refactor `_cascade_halt()` to call `await self.stop_all(graceful=False)` after writing audit entries. Or have `_watch_society_hard_stop()` call both `_cascade_halt()` and `stop_all()`.

---

## Audit Checklist Results

| # | Criterion | Result | Notes |
|---|-----------|--------|-------|
| 1 | Blueprint has 12+ sections | ✅ PASS | 14 sections (§1-§14) |
| 2 | 15 atomic implementation steps defined | ✅ PASS | Steps 1-15 in §3.1-§3.15 |
| 3 | Each step has goal/files/approach/verification/rollback | ✅ PASS | All 15 steps complete with all 5 fields |
| 4 | Config-driven multi-instance architecture specified | ✅ PASS | §4 with per-instance YAML, env vars, forbidden patterns |
| 5 | HPP implementation spec is concrete | ✅ PASS | §5: JSON-RPC 2.0 envelope schema, 11 intents, 5 visibility levels, 6 risk tiers, Redis Streams transport, hash chain, idempotency, example message flow |
| 6 | Discord dual-bot spec is concrete | ✅ PASS | §6: two discord.py.Bot processes, MESSAGE_CONTENT intent, on_message filter rules, rhythm parameters (backoff 2-10s, cooldown 30s, hop cap 4, engage prob 0.70) |
| 7 | Memory spec is concrete (SQL/schema level) | ✅ PASS | §7 + §3.6: 7 migration files with full DDL, RLS policies with FORCE, dedicated `agent_memory_app` role, WORM audit table |
| 8 | Simplified 4-rail life-loop for P28 | ✅ PASS | §8: 4 rails (perception 30s, peer_dialogue 30s, reflection_simple 300s, safety_envelope 1s). Deferred rails explicitly listed with reasons |
| 9 | Safety spec is concrete | ✅ PASS | §9: HARD STOP cascade via Redis DB8 + 1s polling, rate limiting (5 msg/5s/ch), audit hash chain, SHA256 persona anchoring |
| 10 | Verification/evidence plan exists | ✅ PASS | §10: per-step scaffold (12-section verification.md), 3 critical acceptance tests with executable bash, Prometheus/Discord/SQL liveness checks |
| 11 | Rollback plan exists | ✅ PASS | §11: identity rollback, DB rollback SQL, Redis FLUSHDB, Discord rollback, code git revert, RTO <30 min |
| 12 | Risk assessment exists | ✅ PASS | §12: 5 risks (R1-R5) with probability/impact/mitigation/fallback, meta-risk of scope creep |
| 13 | Prerequisites are clear | ✅ PASS | §2: upstream phase status table, VPS/PG/Redis/SOPS requirements, Discord operator setup checklist (6 steps before Step 14) |
| 14 | No step requires P24 fork | ✅ PASS | §2.1 (L97): "NOT NEEDED — P28 uses hybrid adapter + per-instance config (fork is preferred, not required)"; §1.2 (L65): deferred to P32 |
| 15 | No step requires P23 executors | ✅ PASS | §2.1 (L96): "NOT NEEDED — P28 has zero outbound action executors"; §1.2 (L66): deferred to P33 |
| 16 | Plan can be executed by a developer who reads it | ✅ PASS (with F-01 caveat) | All steps have concrete files, commands, expected outputs, code patterns. F-01 requires minor inference |

---

## Minor Observations (Non-Blocking)

### O-1 P27 §18.2 criterion #11 says "7-rail MacroStateScheduler" — P28 blueprint uses 4-rail

P27 plan §18.2 (L3711): "Own autonomy loop: Each agent has its own 7-rail MacroStateScheduler". P28 blueprint §8 (L2393-2404) explicitly scopes down to 4 rails. This is an intentional, well-justified scope reduction (§8.1 explains why each of the 3 deferred rails needs P29+). Not a conflict — the P28 blueprint supersedes the P27 target for implementation purposes.

### O-2 Step 5 `env.conf` drop-in overlaps with main service file `EnvironmentFile=`

Both the main `pharsa-core.service` (L1035) and the drop-in `pharsa-core.service.d/env.conf` (L1097) specify `EnvironmentFile=`. Systemd merges them, so no conflict, but the redundancy is unnecessary. Minor nit.

### O-3 P27 plan §17.4 lists 18 refactor steps; P28 blueprint consolidates to 15 implementation steps

P27 §17.4 (L3631-3651) lists 18 refactor phases (A-R). P28 blueprint §3 (L237-276) consolidates into 15 steps. This is correct — the P27 refactor plan was a *planning inventory*, not an execution order. The P28 blueprint's 15-step structure is the executable form. No conflict.

---

## Recommendations

1. **Fix F-01:** Either create `src/core/society_app.py` in Step 3/4, or change Step 5's `ExecStart` to `src.core.main:app` with per-instance env var routing.

2. **Fix F-02:** Correct `shared_world.retrievability` formula to use `last_accessed_at` instead of the second `now()`.

3. **Fix F-03:** Add `hpp_outbox` and `hpp_inbox` DDL as migration files 008/009 in Steps 8/9, or inline the schemas in the step approach sections.

4. **Fix F-04:** Have `_cascade_halt()` call `stop_all(graceful=False)` to actually halt rail tasks on HARD STOP cascade.

5. **After fixes:** Re-run this audit. All 4 findings are fixable in-place without structural changes to the blueprint.

---

## Acceptance Criteria Mapping

| Audit Criterion | Status |
|---|---|
| P28 blueprint has 12+ sections | ✅ (14 sections) |
| 15 atomic implementation steps | ✅ |
| Each step has goal/files/approach/verification/rollback | ✅ |
| Config-driven multi-instance architecture | ✅ |
| HPP implementation spec is concrete | ✅ |
| Discord dual-bot spec is concrete | ✅ |
| Memory spec is concrete (SQL/schema level) | ✅ |
| Simplified 4-rail life-loop for P28 | ✅ |
| Safety spec is concrete | ✅ |
| Verification/evidence plan exists | ✅ |
| Rollback plan exists | ✅ |
| Risk assessment exists | ✅ |
| Prerequisites are clear | ✅ |
| No P24 fork required | ✅ |
| No P23 executors required | ✅ |
| Developer-executable | ✅ (with F-01 caveat) |

---

## Footer

| Field | Value |
|-------|-------|
| Audit ID | P27-R1-13 |
| Verdict | NEEDS REVIEW |
| Findings | 4 (2 HIGH, 2 MEDIUM) |
| Blocking | No (all fixable in-place) |
| Next Action | Fix F-01 through F-04, then re-audit |
| Auditor | Guinevere (sub-agent) |
| Date | 2026-06-28 |
