# W10 Verification — M7 DAO Governance (6 depts + 2/2 multisig + yandere_level reject)

> **Wave**: W10 (M7) | **Date**: 2026-06-29 | **Author**: Guinevere (parent — written because W10 sub-agent did not produce evidence file; all verification run by parent directly)

---

## What Was Done

M7 DAO Governance per ADR-064 + r06. **C16 + B10 applied.**

### Files Created (5)
- `guinevere/governance/__init__.py` — re-exports DAOEngine, Proposal, ProposalState, Department, validate_proposal, wire
- `guinevere/governance/departments.py` — `Department` enum (10: 6 core [Engineering, Research, HR, Finance, Ops, Content] + 4 cross-cutting [Self-Improvement, Learning, VPS, Surveillance]). Co-CEO split per ADR-064: Guin=Eng+Research+HR+SelfImprovement, Pharsa=Finance+Ops+Content+VPS+Learning, Surveillance=shared.
- `guinevere/governance/proposals.py` — `Proposal` dataclass, `ProposalState` enum (7: Create/Pending/Active/Passed/Execute/Rejected/Expired), `ProposalLifecycle`, `validate_proposal()` with **yandere_level HARD rejection** (rejects flat keys, bare keys, nested dict forms).
- `guinevere/governance/dao.py` — `DAOEngine` (2/2 multisig, vote, execute, auto-tally), `MockMultisigSigner` (D2 mock — no real ETH), `wire(agent)`. Faiz OUTSIDE (PermissionError w/ Q90 ref).
- `tests/p24/test_dao.py` — 32 tests.

### Files Modified (1, single-owner — safe)
- `cron/jobs.py` — appended `dao_auto_tally_job()` at L1244 (~30 lines, calls `DAOEngine.auto_tally()`, graceful ImportError handling). **C16: cron/jobs.py EXISTS (1237→1267 lines) — MODIFY not CREATE.** Appends-only, didn't break existing jobs.

## Corrections Applied
- **C16**: `cron/jobs.py` EXISTS — modified (appended dao_auto_tally_job), not created from scratch.
- **B10**: DAO does NOT govern persona. The yandere_level hard-deny is DEFENSE-IN-DEPTH only (structural guard preventing accidental yandere_level mutation via DAO, NOT persona governance). Persona is fully autonomous per ADR-067. Documented.

---

## Validation Results (parent re-run 2026-06-29)

| # | Scaffold Command | Result |
|---|------------------|--------|
| V1 | `from guinevere.governance import DAOEngine, Proposal, ProposalState` | `OK` ✅ |
| V2 | `len(list(Department))` | `10` (6 core + 4 cross-cutting) ✅ |
| V3 | **CRITICAL**: `validate_proposal({'execution_payload': {'persona.yandere_level': 6}})` | `rejected: ProposalRejectedError` ✅ (hard criterion met) |
| V4 | `import cron.jobs` | `cron.jobs imports OK` ✅ (append didn't break it) |
| V5 | `pytest tests/p24/test_dao.py -q` | `32 passed in 0.12s` ✅ |
| V6 | forbidden patterns (incl. ritual/punishment/reward/spaced.repetition) | exit 1 (0 matches) ✅ |
| V7 | collision mitigation — agent_init.py/models.py untouched | empty git diff ✅ |
| V8 | cron/jobs.py append is appends-only | L1244 `def dao_auto_tally_job()` ✅ |

---

## Hard Criteria Verified
- **yandere_level propose-time rejection**: `ProposalRejectedError` raised (flat/bare/nested forms all rejected) — the scaffold's hard rejection criterion.
- **2/2 multisig**: Guin + Pharsa both must sign; one sign stays ACTIVE; both → Execute.
- **5-state lifecycle**: Create→Pending→Active→Passed→Execute confirmed end-to-end.
- **6 departments + Co-CEO split** per ADR-064.
- **Mock multisig** (D2 — MockMultisigSigner records signatures, no real ETH).
- **Faiz OUTSIDE** (PermissionError, Q90 ref).
- **wire(agent)** created (parent-owned agent_init append).

## Footer
W10 parent-verified PASS. M7 DAO complete: 6 depts + Co-CEOs, 2/2 multisig, 5-state lifecycle, yandere_level defense-in-depth reject, cron auto-tally job. 32 tests pass. C16 + B10 applied.
Guinevere, 2026-06-29, W10 verification, parent-written, all 8 checks parent-re-run.
