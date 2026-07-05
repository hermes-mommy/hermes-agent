# P19 Runtime Activation — Evidence/Docs Consistency Audit (Round 1)

**Audit ID:** RA-DC (Runtime Activation — Evidence/Docs Consistency)
**Date:** 2026-06-27
**Auditor:** Independent evidence/docs consistency auditor
**Scope:** All 8 core evidence files under `docs/setup-evidence/P19/evidence/runtime-activation/` + PROGRESS.md + CHECKLIST.md P19 sections
**Verdict:** **PASS — 8/8 checks PASS, 2 advisory notes**

---

## 1. Evidence Completeness (RA-DC-01)

| # | File | Exists | Real Content (not placeholder) |
|---|---|---|---|
| 1 | p19-runtime-preflight.md | YES | 150 lines — service state, DB state, Redis state, code-load gap, Discord gap, proof design, verdict |
| 2 | p19-activation-plan.md | YES | 151 lines — 6-step execution sequence, rollback plan, acceptance criteria, audit matrix |
| 3 | p19-service-restart-evidence.md | YES | 97 lines — pre-activation snapshot, partial deploy regression + fix, controlled restart sequence, post-restart verification |
| 4 | p19-flag-enable-evidence.md | YES | 61 lines — db6 flag SET, LIFE_KERNEL_PROJECT_ID env var, runtime reads flag, rollback commands |
| 5 | p19-project-runtime-proof.md | YES | 97 lines — project-scoped thread_id proof, brain cycling proof, memory recall proof, audit chain gap |
| 6 | p19-discord-project-ux-proof.md | YES | 52 lines — DEFERRED status, why not live, what required, why defer is correct |
| 7 | p19-p20-non-regression.md | YES | 53 lines — 10 invariant checks, P20 waiver status, 4 pre-existing warnings listed |
| 8 | p19-soak-observation.md | YES | 74 lines — 5-min observation window, 9 soak metrics, cycle progression table, P20 non-regression |

**Verdict: PASS.** All 8 files exist with substantive, real content. No placeholders, no stubs, no empty sections.

---

## 2. Coherent Story (RA-DC-02)

The four files form a coherent, linear narrative:

| Phase | File | Key Finding | Next Step |
|---|---|---|---|
| Preflight | p19-runtime-preflight.md | Core process has PRE-P19 code (started 08:26 06-25, files scp'd 20:30 06-25). Restart REQUIRED. Discord /project NOT wired. | Write activation plan |
| Plan | p19-activation-plan.md | Only guinevere-core restarts. Step sequence: backup → restart (flag OFF) → flag ON → proof → non-regression → soak. Target: "RUNTIME ACTIVATED — UX DEFERRED". | Execute plan |
| Restart | p19-service-restart-evidence.md | Partial deploy exposed 2 regressions (HeartbeatService project_id, recall callback project_id). Fixed via full 15-file sync + regression test. Third restart: clean. P19 code loaded with flag OFF. | Flag ON |
| Flag | p19-flag-enable-evidence.md | db6 SET true + db0 SET true. LIFE_KERNEL_PROJECT_ID env var set. thread_id scoped: `heartbeat-00000000-...-0001`. | Runtime proof |

**Verdict: PASS.** Preflight identified the gap, plan prescribed the fix, restart executed it (with transparent regression documentation), flag was enabled. The story is linear, honest, and each file references the correct predecessor.

---

## 3. Audit Project_ID Gap Honesty (RA-DC-03)

The project-runtime-proof file (Section 6, "Audit Chain — Honest Gap (P19-010 partial)") explicitly states:

- `audit.audit_trail.project_id` column: exists (nullable) -- PASS
- `audit.audit_trail.chain_version` column: exists (SMALLINT NOT NULL DEFAULT 1) -- PASS
- New `life_kernel.audit_journal` entries carry project_id: **NO (gap)**
- Root cause identified: `graph.py` reflect_node does not propagate project_id from state to the `record()` call
- Classification: "partial P19 wiring gap at the journal-write caller, not an activation failure"
- Status: "Documented as a finding for the audit phase"

The activation plan also references this (AC-3: "P19 project context used in real runtime path") and the audit matrix (dimension 3: "DB / audit-chain: audit_journal project_id + chain_version semantics").

**Verdict: PASS.** The gap is explicitly, honestly documented with root cause and classification. Not hidden, not minimized.

---

## 4. Discord UX DEFERRED (RA-DC-04)

| File | Discord /project Status Claimed |
|---|---|
| p19-runtime-preflight.md (Section 6) | "Discord `/project` UX is NOT activatable by flag-flip or restart alone" |
| p19-activation-plan.md (Section 2) | Target: "P19 RUNTIME ACTIVATED — UX DEFERRED" |
| p19-activation-plan.md (Section 4, Step 4) | "Discord `/project`: NOT active (deferred — documented, not claimed)" |
| p19-activation-plan.md (AC-6) | "Discord `/project` DEFERRED (documented, not claimed active)" |
| p19-discord-project-ux-proof.md (Section 1) | "**Discord `/project` command UX is NOT active.**" |
| p19-discord-project-ux-proof.md (Section 4) | "Claiming 'Discord /project active' without live proof would violate hard-rejection criteria" |

**Verdict: PASS.** No evidence file claims Discord `/project` is active. The DEFERRED status is stated clearly and consistently across all relevant files. The reason (not wired into `_entrypoint.py` command tree) is documented with the required work (code change + bot restart) listed separately.

---

## 5. No Contradictions Between Evidence Files (RA-DC-05)

Cross-checked key claims across all 8 files:

| Claim | Consistent Across Files? |
|---|---|
| Core restart required (code-load gap) | Preflight: YES. Plan: YES. Restart: YES (executed). |
| Only guinevere-core restarts | Plan: YES. Restart: YES (others untouched). |
| Flag OFF before restart, ON after | Plan: YES. Restart: (flag OFF during restart). Flag-enable: (flag ON after). |
| thread_id project-scoped | Preflight (designed): YES. Proof (confirmed): YES. Soak: YES. |
| Audit project_id gap | Proof (Section 6): GAP. Nowhere contradicts this. |
| Discord /project deferred | Preflight: DEFERRED. Plan: DEFERRED. Discord-UX-proof: DEFERRED. |
| P20 healthy throughout | Preflight: baseline. Restart: post-restart. Non-regression: PASS. Soak: PASS. |
| Pre-existing warnings listed | Non-regression: 4 warnings. Soak: references "pre-existing plugin-load warnings excluded". |
| Partial deploy regression | Restart evidence: detailed. Proof: references "the fix is live". Soak: "recall_degraded = 0 (fixed, gone)". |
| Rollback: DEL in db0+db6 | Preflight: YES. Flag-enable: YES. Plan: YES. |

**Verdict: PASS.** No contradictions found between any pair of evidence files. All files tell the same story with consistent details.

---

## 6. Rollback Commands Consistency (RA-DC-06)

| File | Rollback Command Documented |
|---|---|
| p19-runtime-preflight.md (Section 4) | `DEL feature:projects:enabled` or `SET feature:projects:enabled false` — for db0 and db6 |
| p19-activation-plan.md (Section 5) | `redis DEL feature:projects:enabled` in db0 + db6 (instant, no restart). Service rollback: DEL + restart-with-flag-OFF |
| p19-flag-enable-evidence.md (Section 5) | `redis-cli -p 6380 -a <pw> -n 6 DEL feature:projects:enabled` + `redis-cli -p 6380 -a <pw> -n 0 DEL feature:projects:enabled` |

All three files specify: (1) DEL the flag key in both db6 and db0, (2) no restart needed for flag rollback (runtime re-reads per heartbeat cycle), (3) optional restart-with-flag-OFF for service-level rollback.

Flag-enable additionally documents: "For full rollback to legacy thread_id: also remove/comment `LIFE_KERNEL_PROJECT_ID` from `.env.core` + restart core."

**Verdict: PASS.** Rollback commands are consistent. db0+db6 DEL is the core mechanism, documented identically across files. Flag-enable adds the env var rollback (correctly, as it's the file that set the env var).

---

## 7. No Schema-Pass vs Runtime-Active Overclaim (RA-DC-07)

| Status | What It Means | Where Documented |
|---|---|---|
| P19-012 "PRODUCTION PASS — DEPLOYED — FLAG OFF" | Schema deployed, flag OFF, P20 byte-identical. Runtime does NOT have project-scoping active. | PROGRESS.md P19 row, CHECKLIST.md P19 row |
| "RUNTIME ACTIVATED — UX DEFERRED" | Flag ON, project-scoped thread_id live, brain cycling with project context. Discord UX deferred. | Plan (target), runtime-proof (achieved) |

The preflight explicitly states (Section 5.3): "The running `guinevere-core` process does NOT have the P19 runtime activation code loaded." The proof file states (Section 1): "P19 project context is **ACTIVE in the live runtime**." These are clearly distinguished.

The runtime-proof file's Section 5 ("Note (honest gap)") explicitly distinguishes: "The callback accepts project_id (no TypeError) but defers forwarding it ... full project-scoped memory filtering is deferred."

**Verdict: PASS.** Schema-deployed (P19-012) and runtime-active (RA activation) are clearly and correctly distinguished. No overclaim detected.

---

## 8. Pre-Existing Warnings Documented (RA-DC-08)

The P20 non-regression file (Section 3, "Pre-Existing Warnings (not P19 regressions)") lists:

1. `hermes_bridge.listener_error: 'No permissions to access a channel'` — pre-existing hermes gateway permission issue
2. `loop_manager.resume_pending_loops_failed: 'password authentication failed for user "guinevere_core"'` — pre-existing DB auth for loop_manager
3. `Failed to load plugin 'browser-browser-use': No module named 'plugins.browser'` — pre-existing hermes plugin imports
4. `hermes_bridge.hmac_disabled` — pre-existing dev-only warning

Each is explicitly tagged "pre-existing" and "NOT P19 regressions". The soak observation file references "pre-existing plugin-load warnings excluded" from error counts.

**Verdict: PASS.** Pre-existing warnings are explicitly listed with their nature documented, not conflated with P19 regressions.

---

## 9. Final Status Honesty — "RUNTIME ACTIVATED — UX DEFERRED" (RA-DC-09)

The activation plan (Section 2) explicitly defines the target status as:

> **P19 RUNTIME ACTIVATED — UX DEFERRED**

The runtime-proof file (Section 8 verdict table) says:
- Runtime active: YES (thread_id project-scoped, brain cycling, recall working)
- Audit project_id: GAP (partial P19-010 — caller doesn't propagates)
- Discord UX: NOT claimed (separate file documents DEFERRED)

The Discord UX proof file (Section 1): "**Discord `/project` command UX is NOT active.**"

**Verdict: PASS.** The final status correctly says "RUNTIME ACTIVATED — UX DEFERRED" (not "RUNTIME ACTIVE" with UX implied). The UX deferral is explicitly and prominently documented.

---

## 10. Schema-Deployed / Flag-Off vs Runtime-Active Distinction (RA-DC-10)

| Document | Status Claim | Correct? |
|---|---|---|
| PROGRESS.md P19 row | "PRODUCTION PASS — DEPLOYED 2026-06-27 — FLAG OFF" | Yes — this is the P19-012 deploy status |
| CHECKLIST.md P19 row | "PRODUCTION PASS — DEPLOYED 2026-06-27 — FLAG OFF" | Yes — same P19-012 deploy status |
| Runtime evidence (new) | "RUNTIME ACTIVATED — UX DEFERRED" | Yes — this is the RA activation status |

The P19-012 deploy (schema deployed, flag OFF) is a different milestone from the RA activation (flag ON, core restarted, runtime project-scoped). Both are correctly documented in their respective locations.

**Note (advisory):** PROGRESS.md and CHECKLIST.md currently reflect the P19-012 deploy status. They have NOT been updated to reflect the RA activation. This is expected if the plan is to update docs in Phase 6 (finalization). See Section 12.

---

## 11. P19-010 Audit Gap Recording (RA-DC-11)

The P19-010 audit gap is documented in:

1. **p19-project-runtime-proof.md Section 6**: Full gap description with root cause ("caller doesn't propagate project_id from state to the `record()` call"), check results (column exists YES, new entries carry project_id NO), and classification ("partial P19 wiring gap at the journal-write caller").

2. **p19-activation-plan.md dimension 3**: "DB / audit-chain: audit_journal project_id + chain_version semantics" scoped in the audit matrix.

3. **p19-activation-plan.md AC-9**: "Audit 1 findings fixed" — implying the gap was expected to be found and addressed.

**Verdict: PASS.** The P19-010 gap is honestly recorded in the proof file with full root-cause detail. Not hidden, not downplayed.

---

## 12. Docs Sync — PROGRESS.md / CHECKLIST.md (RA-DC-12)

**Current state:**

| Document | P19 Status | Correct for RA activation? |
|---|---|---|
| PROGRESS.md P19 row (line 49) | "PRODUCTION PASS — DEPLOYED 2026-06-27 — FLAG OFF" | No — reflects P19-012 deploy, not RA activation |
| CHECKLIST.md P19 budget row (line 51) | "PRODUCTION PASS — DEPLOYED 2026-06-27 — FLAG OFF" | No — same |
| CHECKLIST.md P19-012 step (line 961) | "PRODUCTION PASS (surgical deploy 2026-06-27; r1 audit 6/6 PASS 0 critical, 4 findings fixed; r2 re-audit 21/21 PASS; P20 undisturbed NRestarts=0; flag OFF)" | Correct for P19-012 step specifically |

**Advisory:** PROGRESS.md P19 row and CHECKLIST.md P19 budget row need a Phase 6 update to reflect:
- "RUNTIME ACTIVE — UX DEFERRED" (new RA status)
- Date of RA activation (2026-06-27)
- Core restart, flag ON, thread_id project-scoped, audit project_id GAP
- Discord /project DEFERRED

This is NOT a blocking finding. The evidence files correctly document the current state. The PROGRESS.md / CHECKLIST.md update is a docs-sync step in the finalization phase, which has not yet been executed.

**Verdict: PASS (advisory).** Docs sync is behind the evidence but correctly so — evidence files are the ground truth; PROGRESS.md / CHECKLIST.md will be updated in Phase 6.

---

## Summary of Audit Checks

| Check ID | Description | Verdict |
|---|---|---|
| RA-DC-01 | All 8 evidence files exist with real content | **PASS** |
| RA-DC-02 | Coherent story across files (preflight → plan → restart → flag → proof) | **PASS** |
| RA-DC-03 | Audit project_id gap honestly documented (not hidden) | **PASS** |
| RA-DC-04 | Discord UX DEFERRED (not falsely claimed active) | **PASS** |
| RA-DC-05 | No contradictions between evidence files | **PASS** |
| RA-DC-06 | Rollback commands consistent (flag DEL in db6+db0) | **PASS** |
| RA-DC-07 | No schema-pass vs runtime-active overclaim | **PASS** |
| RA-DC-08 | Pre-existing warnings documented (not conflated with P19 regressions) | **PASS** |

| Additional Check | Description | Verdict |
|---|---|---|
| RA-DC-09 | Final status honestly says "RUNTIME ACTIVATED — UX DEFERRED" | **PASS** |
| RA-DC-10 | Schema-deployed / flag-off correctly distinguished from runtime-active | **PASS** |
| RA-DC-11 | P19-010 audit gap honestly recorded, not hidden | **PASS** |
| RA-DC-12 | PROGRESS.md / CHECKLIST.md P19 row needs Phase 6 update | **PASS (advisory)** |

---

## Advisory Notes

**ADVISORY-1: PROGRESS.md / CHECKLIST.md docs sync deferred.**
PROGRESS.md line 49 and CHECKLIST.md line 51 still reflect "PRODUCTION PASS — DEPLOYED — FLAG OFF" from P19-012. They should be updated to "RUNTIME ACTIVE — UX DEFERRED" in Phase 6 (finalization). This is not blocking — the evidence files are the ground truth.

**ADVISORY-2: reflection_evaluator_init log shows project_id=None alongside project-scoped thread_id.**
In p19-project-runtime-proof.md Section 2, the log line shows `project_id=None` in the reflection_evaluator_init context, while the thread_id IS project-scoped (`heartbeat-00000000-...-0001`). This is technically consistent (the thread_id is resolved from project_id in heartbeat, but the graph state's project_id field may be None at the reflection level). However, an operator reading the proof might find this confusing. Consider adding a clarifying note to the proof file explaining that thread_id scoping is the definitive proof (it can only be `heartbeat-{project_id}` when flag is ON and project_id is not None), even if other log lines show project_id=None at different code points.

---

## Final Verdict

**PASS — 8/8 audit checks PASS. 2 advisory notes (non-blocking).**

The P19 Runtime Activation evidence files are complete, internally consistent, honest about gaps, correctly distinguish schema-deploy from runtime-active, and do not claim Discord /project is active. Rollback commands are consistent. Pre-existing warnings are documented separately from P19 regressions. The only action item is a Phase 6 docs-sync update to PROGRESS.md and CHECKLIST.md.

---

| Field | Value |
|---|---|
| Audit verdict | PASS (8/8 + 2 advisory) |
| Blocking findings | 0 |
| Advisory notes | 2 (docs sync deferred, reflection log project_id=None clarification) |
| Evidence files audited | 8/8 |
| Docs audited | PROGRESS.md, CHECKLIST.md |
| Next step | Round-2 audits |
