# P23 Audit Round 1 — Rollback / Idempotency

> **Auditor:** Independent auditor (subagent)  
> **Date:** 2026-06-25  
> **Audit Scope:** Rollback, idempotency, retry/backoff, cancel mechanisms, backup gates  
> **Phase:** P23 Planning Phase (definition-only; no runtime implementation audit)

---

## 1. Audit Scope

This audit evaluates the P23 Embodied Operations / Personal OS Action Layer planning phase for completeness, consistency, and compliance with ground-truth requirements in the rollback and idempotency domain.

**Audit subjects:**
- **Plan:** `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md` (sections 6, 25, 29, 32, 39, 46)
- **Research:** `docs/setup-evidence/P23/research/p23-rollback-idempotency-research.md`
- **Ground truth:** AGENTS.md §0.1 (invariants 3-4), §2.11; ADR-029 (self-mod testing); ADR-025/032 (backup DR); ADR-035 (sentinel `/home/guinevere/.backup/last-success`); `src/life_kernel/self_improve.py` (RegressionGate)

**Audit dimensions:**
1. Action lifecycle state-machine: queued→scheduled→pre-flight→running→{succeeded|failed|rolled-back|cancelled|timed-out}+dead-letter? Terminal states immutable? (hard-rejection #3)
2. Retry/backoff: exponential+jitter? max_retries per tier (L1=3, L2=2, L3=1+escalate, L4=0)? dead-letter on exhaustion?
3. Cancel: HARD STOP + explicit cancel via p23:cancel pub/sub? running actions abort mid-step? queued drain-cancel? (hard-rejection #3, #9)
4. Per-executor rollback: browser (close/restore DOM), desktop (kill/restore file), VPS (restore backup/systemctl revert/sentinel), GitHub (revert PR/delete branch), filesystem (restore from backup/trash), external (API undo/compensate)? (hard-rejection #3)
5. L3 backup-before-execute (§0.1 invariant 3): every L3 creates backup BEFORE; backup fails → block?
6. Rollback-before-promote (§0.1 invariant 4, ADR-029): self-mod passes regression before promote; rollback target = last known-good?
7. Idempotency: (namespace+intent_hash) dedup? at-least-once + idempotent side effects? scripts/migrations re-run safe (§2.11)?

---

## 2. Findings

### Finding 1: Action Lifecycle State-Machine — PASS

**Severity:** N/A (compliant)

**Location:** Plan §6 (lines 122-134), Research §3.1 (lines 54-127)

**Evidence:**
- Complete state-machine defined: `queued → scheduled → pre-flight → running → {succeeded | failed | rolled-back | cancelled | timed-out | dead-letter}`
- Terminal states explicitly documented as immutable (Research §3.1, line 128: "Terminal states are immutable")
- PostgreSQL WORM enforcement: `REVOKE UPDATE, DELETE ON p23.action_queue FROM guinevere_core` (Plan §32, Research §3.2.1 DDL)
- State transitions include retry loop with backoff between `failed` and `scheduled`
- Dead-letter state on retry exhaustion documented (Plan §6, Research §3.3)

**Assessment:** The lifecycle state-machine is complete, deterministic, and enforces terminal state immutability via database-level WORM. Hard-rejection criterion #3 satisfied.

**Recommendation:** None (compliant).

---

### Finding 2: Retry/Backoff Policy — PASS with CAVEAT

**Severity:** LOW (missing implementation detail)

**Location:** Plan §29 (lines 449-465), Research §3.3 (lines 290-320)

**Evidence:**
- Exponential backoff + full jitter documented: Research §3.3 includes Python implementation `compute_backoff(retry_count, base, max_delay)` with `random.uniform(0, exp_delay)`
- max_retries per tier: L1=3, L2=2, L3=1+escalate, L4=0 (Plan §29 table, Research §3.3 table)
- Dead-letter on exhaustion: Research §3.3 "after `max_retries` exhausted, action moves to `p23.action_dead_letter`"
- Retry eligibility checks documented (Research §3.3 lines 310-315): retry_count < max, error is retryable, HARD STOP not active, cancel not requested, idempotency key not already succeeded

**Caveat:** Plan §32 DDL includes `CHECK (risk_tier != 'L4' OR max_retries = 0)` constraint enforcing L4=0 retries, but does not include similar CHECK constraints for L1=3, L2=2, L3=1. Implementation wave must add validation that enqueue/scheduler respects tier-specific max_retries or add CHECK constraints.

**Assessment:** Retry/backoff policy is complete and grounded. Minor implementation gap (no DDL constraint enforcement for L1-L3 max_retries) does not block planning phase but should be tracked for P23-003 (durable queue implementation).

**Recommendation:** Add to P23-003 verification scaffold: "Enqueue must enforce max_retries per tier: L1=3, L2=2, L3=1+escalate. Verify via unit test that L2 action with max_retries=3 is rejected at enqueue."

---

### Finding 3: Cancel Mechanisms — PASS

**Severity:** N/A (compliant)

**Location:** Plan §25 (lines 363-375), Research §3.3 (lines 319-322)

**Evidence:**
- **HARD STOP:** Redis `life_kernel:hard_stop` as single source of truth; executors check pre-action + between steps + subscribe to `p23:cancel` pub/sub (Plan §25 bullet 2)
- **Explicit cancel:** `SET p23:action:cancel:{action_id} 1 EX 60` → executor checks flag in poll loop → transitions to `cancelled` (Research §3.3, Redis key layout section)
- **Mid-action abort:** Plan §25 bullet 2 explicitly states "running actions abort mid-step" and "queued actions drain-cancel"
- **Queue drain on HARD STOP:** Plan §25 bullet 3 "on HARD STOP, the action queue stops dequeuing new actions; all `queued` actions transition to `cancelled`"
- **Non-bypassable:** Plan §25 invariant 3 "HARD STOP cannot be bypassed by autonomy"

**Assessment:** Cancel mechanisms satisfy hard-rejection criteria #3 and #9. Both HARD STOP (global) and explicit cancel (per-action) paths defined. Mid-action abort and queue drain documented. Hard-rejection criterion #9 satisfied.

**Recommendation:** None (compliant).

---

### Finding 4: Per-Executor Rollback — PASS with NOTE

**Severity:** N/A (compliant with documented limitation)

**Location:** Plan §29 (lines 452-462), Research §3.4 (lines 323-339)

**Evidence:**
- **Browser:** Close page/restore DOM snapshot; limitation documented "Can't undo external side effects (e.g., form submission that already hit server)"
- **Desktop:** Kill process/restore file from workspace trash; limitation "Can't undo network side effects"
- **VPS:** Restore from backup (pg_dump/S3/R2), systemctl revert, sentinel `/home/guinevere/.backup/last-success`; documents RTO (large DB restores take minutes)
- **GitHub:** Revert PR (`gh pr revert` or `git revert`), delete branch; limitation "Can't undo if PR already merged to protected branch without force-push rights. Rollback = revert commit (new commit that undoes changes)"
- **Filesystem:** Restore from trash copy or workspace backup snapshot; limitation "Trash has size limit (configurable, default 1GB)"
- **External API:** API undo endpoint where supported, else compensating action; limitation documented "Many APIs have no undo. Compensating actions must be idempotent themselves. If neither undo nor compensate possible, mark `rollback_state = 'unavailable'` and escalate."

**NOTE:** Research §3.4 table explicitly documents limitations and `rollback_state = 'unavailable'` escape hatch for non-rollbackable actions. This is acceptable design — not all actions are reversible, and the plan correctly escalates rather than pretending rollback is always possible.

**Assessment:** Per-executor rollback strategies are documented for all 6 executors with realistic limitations. Hard-rejection criterion #3 satisfied (rollback paths exist; unavailable cases escalate rather than fail silently).

**Recommendation:** None (compliant). The `rollback_state = 'unavailable'` handling is good design, not a gap.

---

### Finding 5: L3 Backup-Before-Execute Gate — PASS

**Severity:** N/A (compliant)

**Location:** Plan §29 (lines 461-462), Research §3.5 (lines 341-404), Plan §32 DDL (lines 491-515)

**Evidence:**
- **AGENTS.md §0.1 invariant 3:** "all autonomous deployments produce backup + rollback evidence before promotion" (AGENTS.md lines 87)
- **Plan enforcement:** "L3 backup-before-execute gate (AGENTS.md §0.1 invariant 3): every L3 action creates a backup BEFORE; backup must complete and verify (S3/R2 upload confirmed) BEFORE action transitions to `running`. If backup fails → action stays `queued`, alert fired, no execution." (Plan §29, lines 461-462; Research §3.5 L3 backup-before-execute gate)
- **DDL constraint:** `CONSTRAINT chk_l3_backup_required CHECK ((risk_tier != 'L3' AND risk_tier != 'L4') OR (rollback_payload IS NOT NULL AND rollback_payload ? 'backup_ref'))` (Plan §32, Research §3.2.1 DDL line ~213)
- **Deploy gate sequence:** Research §3.5 documents full gate: BACKUP → verify rclone check → CANARY → smoke tests → PROMOTE or ROLLBACK

**Assessment:** L3 backup-before-execute is mandated by CHECK constraint at database level and documented in deploy gate sequence. AGENTS.md §0.1 invariant 3 satisfied.

**Recommendation:** None (compliant).

---

### Finding 6: Rollback-Before-Promote (Self-Mod) — PASS

**Severity:** N/A (compliant)

**Location:** Plan §29 (lines 462-463), Research §3.5 (lines 406-412), ADR-029 (self-mod testing), `src/life_kernel/self_improve.py` (RegressionGate)

**Evidence:**
- **AGENTS.md §0.1 invariant 4:** "all autonomous self-modifications pass regression tests before promotion" (AGENTS.md line 88)
- **Plan enforcement:** "Rollback-before-promote (§0.1 invariant 4, ADR-029): self-mod actions pass regression (`pytest`) before promote; rollback target = last known-good (commit SHA / sentinel / snapshot)." (Plan §29, lines 462-463)
- **ADR-029:** "If any automated test fails after deployment, the system performs an automatic `git revert` to the last known-good commit. Rollback must complete within 60 seconds." (ADR-029 lines 105-108)
- **RegressionGate implementation:** `src/life_kernel/self_improve.py` lines 264-363 implements `RegressionGate.run_regression_tests()` → `promote()` → `rollback()` flow. Test command: `python -m pytest tests/life_kernel/ -q --tb=short` (line 272). `promote()` returns False if tests fail, triggering `rollback()` which marks candidate as `rejected` (lines 335-363).
- **Research §3.5:** "Self-modification gate (ADR-029, AGENTS.md §0.1 invariant 4): All autonomous self-modifications MUST pass regression tests before promotion. Test categories: unit, integration, safety boundary, regression. Safety-critical changes (persona, safety boundary, surveillance, encryption, memory access, loop governance) require explicit Faiz review regardless of test results. Rollback target = last known-good commit (`git revert`)."

**Assessment:** Self-modification regression gate is fully specified and implemented in runtime code (`self_improve.py`). ADR-029 60-second rollback SLO documented. AGENTS.md §0.1 invariant 4 satisfied.

**Recommendation:** None (compliant).

---

### Finding 7: Idempotency — PASS with IMPLEMENTATION NOTE

**Severity:** N/A (compliant with implementation note)

**Location:** Plan §7 (lines 136-144), Plan §29 (lines 463), Research §3.6 (lines 414-455)

**Evidence:**
- **Idempotency key:** `idempotency_key = namespace + ':' + intent_hash` where `intent_hash = SHA256(canonical_json(payload))` (Research §3.6 lines 416-434)
- **Dedup enforcement:** `UNIQUE (namespace, intent_hash)` index on `p23.action_queue` WHERE status IN active states (Plan §32, Research §3.2.1 DDL line ~218)
- **At-least-once + idempotent side effects:** Research §3.6 lines 442-451 documents executor-specific idempotency patterns: browser (check page state), external_api (provider idempotency keys), github (check PR/commit exists), filesystem (content hash), vps_ssh (service state)
- **AGENTS.md §2.11 compliance:** "Scripts, migrations, evidence generators, and setup steps must be re-run safe or document one-shot behavior and rollback." Research §3.6 lines 452-454 documents one-shot actions: `payload.one_shot = true` and `max_retries = 0`

**Implementation Note:** Research §3.6 lines 442-451 documents idempotency *patterns* per executor, but Plan §46 per-wave scaffolds do not explicitly include "verify idempotent re-run" in Required Commands for executors. E.g., P23-005 (browser) scaffold should include: "Run action twice with same intent_hash; verify second invocation is no-op or returns existing action_id."

**Assessment:** Idempotency design is complete (key construction, dedup index, side-effect patterns, one-shot documentation). Minor implementation gap: per-wave scaffolds should explicitly test idempotency during executor implementation. Does not block planning phase.

**Recommendation:** Add to P23-004 (executor base contract) verification scaffold: "BaseExecutorAdapter.execute() must be idempotent or document one-shot with max_retries=0. Unit test: call execute() twice with same payload; verify no duplicate side effects." Add to P23-005..009 (per-executor) scaffolds: "Verify executor-specific idempotency pattern from Research §3.6."

---

### Finding 8: Sentinel Path `/home/guinevere/.backup/last-success` — PASS with CAVEAT

**Severity:** LOW (documented risk accepted)

**Location:** Research §3.4 (VPS rollback), ADR-035 B11 caveat

**Evidence:**
- **Sentinel usage:** Research §3.4 VPS rollback row: "update sentinel `/home/guinevere/.backup/last-success`" (line 329). Research §3.5 L3 deploy gate: "Update sentinel: echo \"{action_id}\" > /home/guinevere/.backup/last-success" (line 383)
- **ADR-035 B11 caveat:** Research §5.7 documents "The sentinel `/home/guinevere/.backup/last-success` is verified but has an accepted risk: offline age-key recovery and `secrets/backup/` restoration are not yet re-enabled for encrypted S3/R2 restore. **Risk**: L3 rollback may fail if backup restore requires encrypted secrets not yet available. **Mitigation**: document this as a blocker for encrypted-backup L3 rollbacks; plaintext backups (pg_dump) work; encrypted file snapshots may not until B10 is resolved."

**Assessment:** Sentinel path is used consistently for VPS rollback target. ADR-035 B11 caveat documents a known limitation (encrypted backup restore) that is accepted risk, not a planning gap. Plaintext backups (pg_dump) are confirmed working.

**Recommendation:** Track ADR-035 B10 resolution as a blocker for encrypted-file L3 rollbacks. Plaintext DB backups unaffected; can proceed with L3 VPS executor using pg_dump only.

---

### Finding 9: Dead-Letter Queue Handling — PASS

**Severity:** N/A (compliant)

**Location:** Plan §29 (lines 463-465), Research §3.3 (lines 317-318), Research §3.2.2 (DDL)

**Evidence:**
- **Dead-letter trigger:** "after `max_retries` exhausted, action moves to `p23.action_dead_letter` with `last_error`, `resolved=FALSE`" (Research §3.3)
- **Dead-letter table schema:** Research §3.2.2 lines 241-265 defines `p23.action_dead_letter` with fields: action_id, namespace, executor, intent, risk_tier, final_status, payload, retry_count, max_retries, last_error, created_at, moved_to_dlq_at, correlation_id, inspector_notes, resolved
- **Inspector workflow:** "Inspector (operator or autonomous review) marks `resolved=TRUE` after manual intervention" (Research §3.3 line 318)
- **Plan documentation:** Plan §29 lists "dead-letter on exhaustion" as consequence of retry policy

**Assessment:** Dead-letter queue is fully specified with dedicated table, inspector workflow, and resolved flag. Exhausted actions escalate rather than silently drop.

**Recommendation:** None (compliant).

---

### Finding 10: Audit Trail for Rollback — PASS

**Severity:** N/A (compliant)

**Location:** Plan §27 (lines 393-437), Research §3.7 (lines 456-593)

**Evidence:**
- **Hash-chained audit:** `audit.p23_action_log` extends P22 pattern with `previous_hash` + `event_hash` (Research §3.7.1 DDL lines 462-511)
- **Rollback-specific fields:** `rollback_state`, `rollback_reason`, `backup_ref` captured in audit events (Research §3.7.1 DDL line 489-491)
- **WORM enforcement:** `REVOKE UPDATE, DELETE ON audit.p23_action_log FROM guinevere_core` (Research §3.7.1 line 505)
- **Per-transition audit:** Research §3.7.3 table (lines 569-583) documents audit events for every state transition including `→ rolled-back` with reasoning/backup_ref/restore verification
- **Reasoning journal dual surface:** Plan §27 distinguishes "WHY" (reasoning journal) vs "WHAT/WHEN/WHO" (compliance audit log) (lines 398-402)

**Assessment:** Audit trail satisfies AGENTS.md §0.1 invariant 2 ("autonomous actions produce audit trail") and tamper-evidence requirement. Rollback events captured with full context.

**Recommendation:** None (compliant).

---

## 3. Hard-Rejection Criteria Check

Plan §45 defines 19 hard-rejection criteria. This audit focuses on criteria related to rollback/idempotency:

| Criterion | Status | Evidence |
|---|---|---|
| **#3: Action queue lacks retry/backoff/cancel/rollback state** | **PASS** | Finding 1 (lifecycle), Finding 2 (retry/backoff), Finding 3 (cancel), Finding 4 (per-executor rollback) |
| **#9: HARD STOP does not cancel running/queued actions** | **PASS** | Finding 3 (HARD STOP pre+mid-action checks, queue drain, pub/sub cancel) |
| **#12: Destructive/write/deploy action lacks backup/canary/smoke/rollback policy** | **PASS** | Finding 5 (L3 backup-before-execute), Finding 6 (self-mod regression gate), Research §3.5 (deploy gate sequence) |

**Additional criteria verified:**
- AGENTS.md §0.1 invariant 3 (backup before promote): **PASS** (Finding 5)
- AGENTS.md §0.1 invariant 4 (regression before self-mod promote): **PASS** (Finding 6)
- AGENTS.md §2.11 (idempotency/re-run safety): **PASS** (Finding 7)
- ADR-029 (self-mod automated testing + 60s rollback): **PASS** (Finding 6)

**Verdict:** All hard-rejection criteria related to rollback/idempotency are satisfied.

---

## 4. Verdict + Summary

**VERDICT: PASS**

The P23 planning phase fully satisfies all rollback and idempotency requirements from ground-truth sources (AGENTS.md §0.1, §2.11; ADR-029; ADR-025/032/035; RegressionGate runtime code). All hard-rejection criteria (#3, #9, #12) are met.

**Key strengths:**
1. Complete action lifecycle state-machine with terminal state immutability enforced at database level (WORM)
2. Exponential backoff + full jitter with tier-specific retry limits (L1=3, L2=2, L3=1+escalate, L4=0)
3. Dual cancel paths (HARD STOP global + explicit per-action) with mid-step abort and queue drain
4. Per-executor rollback strategies with documented limitations and `unavailable` escalation
5. L3 backup-before-execute enforced by DDL CHECK constraint + deploy gate sequence
6. Self-mod regression gate (ADR-029 + RegressionGate runtime) with 60-second rollback SLO
7. Idempotency via `(namespace, intent_hash)` dedup + at-least-once + idempotent side effects
8. Hash-chained audit trail (WORM) capturing all rollback events with reasoning + backup_ref
9. Dead-letter queue for exhausted retries with inspector workflow

**Minor implementation notes (non-blocking):**
- **Finding 2 caveat:** DDL CHECK constraint enforces L4=0 but not L1=3, L2=2, L3=1. Track for P23-003 scaffold.
- **Finding 7 note:** Per-wave scaffolds should explicitly test idempotency re-run. Track for P23-004..009 scaffolds.
- **Finding 8 caveat:** ADR-035 B11 caveat (encrypted backup restore) is accepted risk; plaintext pg_dump unaffected.

**Audit output path:** `docs/setup-evidence/P23/evidence/audits/round-1/rollback-idempotency.md`

---

**Auditor signature:** Independent auditor (subagent), 2026-06-25  
**Review status:** Round 1 complete; no blocking findings; minor implementation notes tracked for wave scaffolds
