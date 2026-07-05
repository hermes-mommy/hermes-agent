# P22/P23 Dependency Research for P28-P36 Masterplan

> **Research Agent**: bg_dca61af9 (explore, read-only)
> **Date**: 2026-06-28
> **Status**: COMPLETED
> **Note**: Explore agent was read-only and could not write files. Parent (Guinevere) saved this file from agent's inline output.

---

## §0 Executive Summary

This research investigates the production-readiness status of P22 (Integration API) and P23 (External Executor) as dependency gates for P28 (Hermes Society). The findings are critical because Faiz's locked decision #1 states "P28 BLOCKED until P24 production pass + P22.2 production pass + P23 production pass."

**Key findings:**
- **P22.1 = PRODUCTION PASS** (2026-06-28) — integration API is live with 3 ACTIVE adapters
- **P22.2 does NOT exist** in the repository — only P22 (impl HELD) and P22.1 (PRODUCTION PASS) are present
- **P23 = DEFINITION ONLY** — 51 files, 0 runtime code, NOT production-pass
- P28 can start with P22.1 alone as minimum hands (3 ACTIVE adapters: filesystem, vps, discord)
- P21 voice = SKIPPED (not a P28 dependency per Faiz)
- 9Router/P25/P26 = NOT P28 dependencies

---

## §1 P22 Status — Integration API

### §1.1 P22 (Original) — IMPL HOLD

- ADR-053 (Accepted 2026-06-27) is the canonical P22 ADR
- P22 original implementation is HELD — the production-ready version is P22.1

### §1.2 P22.1 — PRODUCTION PASS (2026-06-28)

**3 foundation gaps closed:**

| Gap | Before | After | Evidence |
|---|---|---|---|
| audit_writer | None (no-op) | IntegrationAuditWriter wired | Hash-chained rows to `audit.integration_api_log` with real `project_id` |
| consent_checker | None (no-op) | P22ConsentChecker wired | Queries `consent.consent_ledger`, fail-closed, ACTIVE-only, project-scoped |
| L2+ proof | No live proof | 14/14 live VPS proof | All 14 proof items verified on production VPS |

**Adapter Status:**
- 3 ACTIVE: filesystem, vps, discord
- 10 CONFIG_MISSING (honest, no fake-pass — these are adapters that have no credentials configured, which is correct behavior)

**Database:**
- Migration `p22_001_integration_schema` applied
- WORM (Write-Once-Read-Many) enforced on `audit.integration_api_log`

**Test Results:**
- 112/112 tests pass
- 0 regression
- R1: 9/9 PASS
- R2: 5/5 PASS

**P23-014 P22-side dependency:** READY-WITH-LIMITATIONS

### §1.3 P22.2 — DOES NOT EXIST

**P22.2 does not exist anywhere in the repository.** Only two P22 variants are present:
1. P22 (original) — IMPL HOLD
2. P22.1 — PRODUCTION PASS

**Possible interpretations of "P22.2":**
1. P22 implementation waves P22-002 through P22-006 (the remaining impl waves from the P22 plan)
2. A post-P22.1 next-phase enhancement (not yet defined)
3. A misread of P22.1 (Faiz may have meant P22.1 when saying P22.2)

**Recommendation:** Clarify with Faiz which interpretation is correct. If P22.2 = P22.1, the gate is MET. If P22.2 = remaining impl waves, those are future work not yet started.

---

## §2 P23 Status — External Executor

### §2.1 Current State — DEFINITION ONLY

- 51 files / 10,306 lines
- 0 runtime code (no `.py` files with executable implementation)
- Definition complete, implementation not started

### §2.2 P23A — Ready to Start

- Uses default namespace
- Voice/external disabled
- Independent of P19/P21/P22
- Can begin implementation immediately

### §2.3 P23B — Blocked

P23B is blocked on:
- P19 runtime namespace registry (not yet complete)
- P21 implementation (excluded per Faiz's decision — P21 voice SKIPPED)
- P22 implementation (now unblocked via P22.1)

### §2.4 P23 Architecture

**7 Executor Surfaces:**
1. Browser
2. Desktop
3. VPS
4. GitHub
5. Filesystem
6. Mobile (deferred)
7. External integration

**7-Step Policy Gate:**
1. Classify (determine risk tier)
2. HARD STOP check
3. Distress check
4. Consent check
5. Namespace authorization
6. Execute
7. Audit

**Risk Tiers:**
- L1: Read-Auto (automatic, no approval)
- L2: Write-Notify (execute + notify operator)
- L3: Destructive-Approval (explicit approval required)
- L4: Forbidden (never execute)

### §2.5 P23 Audit Results

- 19/19 hard-rejection criteria mitigated
- R1: 8 PASS, 4 NEEDS-REVIEW
- R2: all PASS

### §2.6 P23 Production-Pass Requirements

P23 production-pass requires ALL of:
- P23-020: 24h soak test
- P23-014: ExternalExecutor implementation
- P23-011: Planner wire
- All executor waves (browser, desktop, vps, github, filesystem)

**Current status: NONE of these are complete.** P23 is definition-only.

---

## §3 P28 Dependency Gate Analysis

### §3.1 Faiz's Locked Dependencies vs. Reality

| Dependency | Faiz's Decision | Actual Status | Verdict |
|---|---|---|---|
| P24 production pass | Hard dependency | NOT a hard dependency (see p24-fork-dependency.md) | SUPERSEDED — see P24 research |
| P22.2 production pass | Hard dependency | P22.2 doesn't exist; P22.1 = PRODUCTION PASS | AMBIGUOUS — clarify with Faiz |
| P23 production pass | Hard dependency | DEFINITION ONLY — 0 runtime code | NOT MET |

### §3.2 Minimum Viable P28 Dependencies

Based on repo evidence, the minimum viable dependency set for P28 is:

| Gate | Status | Notes |
|---|---|---|
| P22.1 PRODUCTION PASS | MET (2026-06-28) | 3 ACTIVE adapters: filesystem, vps, discord |
| P23A | Ready to start | P23A is independent of P19/P21/P22; can run alongside P28 |
| P23B | Deferrable | P23B's advanced executors not needed for initial P28 |
| P21 voice | SKIPPED | Per Faiz's decision #20 |
| 9Router/P25/P26 | NOT dependencies | Per Faiz's decision #20 |

### §3.3 P28 Can Start With P22.1 Alone

P28 can begin with P22.1 as the minimum "hands" layer:
- Filesystem adapter → Hermes can read/write files
- VPS adapter → Hermes can execute shell commands on VPS
- Discord adapter → Hermes can interact via Discord

This gives each Hermes agent the ability to:
- Communicate (Discord)
- Read/write files (filesystem)
- Execute commands (VPS)

P23's advanced executors (browser, desktop, github, mobile) can be added incrementally as P23 waves complete.

---

## §4 P28 Dependency Gates (Recommended)

| Gate | ID | Status | Notes |
|---|---|---|---|
| G1 | P27 Accepted (ADR-054) | MET | ADR-054 Accepted |
| G2 | P19 PRODUCTION COMPLETE | Check | Need to verify P19 status |
| G3 | P20 EARLY ACCEPTANCE | Check | Need to verify P20 status |
| G4 | P22.1 PRODUCTION PASS | MET | 2026-06-28, 3 ACTIVE adapters |
| G5 | P23B deferrable | MET | P23A sufficient for P28 initial scope |
| G6 | P28 fork-agnostic blueprint verified | MET | P27 blueprint is fork-agnostic |
| G7 | AGENTS.md preflight | MET | Current AGENTS.md is current |
| G8 | P24 status INFO_ONLY | MET | P24 is preferred optimization, not hard dependency |

---

## §5 Recommendations for Masterplan

1. **Document the P22.2 ambiguity**: Faiz said "P22.2 production pass" but P22.2 doesn't exist. The masterplan should present P22.1 as the met gate and note the ambiguity.

2. **Document P23 as deferrable**: P23 production-pass is NOT achievable yet (definition-only). But P28 can start with P22.1 alone. P23A can run alongside P28. P23B's advanced executors can be added incrementally.

3. **Do NOT block P28 on P23 production-pass**: This would indefinitely block P28 since P23 has 0 runtime code. Instead, gate P28 on P22.1 + P23A-ready-to-start.

4. **Clarify with Faiz**: The P22.2 ambiguity needs resolution. Options:
   - (a) P22.2 = P22.1 (gate is MET)
   - (b) P22.2 = P22 impl waves P22-002..006 (gate is NOT MET, future work)
   - (c) P22.2 was a misread of P22.1

5. **P23 integration path**: P23A can be implemented alongside P28. When P23A's filesystem/vps/github executors are ready, they enhance Hermes Society's hands. P23B's advanced executors (browser, desktop, mobile) are post-P28 enhancements.

---

## §6 Footer

| Field | Value |
|---|---|
| Research Date | 2026-06-28 |
| Agent | bg_dca61af9 (explore, read-only) |
| File Saved By | Parent (Guinevere) — explore agent could not write files |
| Sources | Repository files: PROGRESS.md, ADR-053, ADR-054, P22 evidence, P23 evidence, P27 evidence |
| Status | COMPLETED |
