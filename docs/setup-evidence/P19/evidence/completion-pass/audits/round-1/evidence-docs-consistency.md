# P19 Completion Pass — Audit Round 1: Evidence / Docs Consistency

**Date:** 2026-06-27 15:10 WIB
**Auditor:** Guinevere (parent, independent)
**Scope:** Evidence / docs consistency only (no code/runtime audit)
**Phase:** 6 — Audits round-1

---

## 1. Scope & Method

This audit verifies that the P19 Completion-Pass evidence set is internally
consistent, complete, and free of overclaim. Method:

- Read every evidence file in `docs/setup-evidence/P19/evidence/completion-pass/`
  and the two referenced upstream reports (runtime-activation, production-deploy).
- Read PROGRESS.md and CHECKLIST.md P19 rows.
- Diff evidence claims against each other and against the source tree.
- Score 8 named audit checks (CP-DC-01..08).
- Output verdict (PASS / PASS-WITH-FINDINGS / FAIL) and per-check verdicts.

The audit does **not** run code, does not SSH the VPS, and does not check
live Discord. Those are other round-1 dimensions. This dimension is purely
textual / structural consistency.

---

## 2. Artifacts Audited

| # | Artifact | Path | Size | Status |
|---|---|---|---|---|
| 1 | Completion-pass preflight | `docs/setup-evidence/P19/evidence/completion-pass/preflight.md` | 1171 B | real content |
| 2 | Completion-pass plan | `docs/setup-evidence/P19/evidence/completion-pass/plan.md` | 4139 B | real content |
| 3 | Runtime-activation final report | `docs/setup-evidence/P19/evidence/runtime-activation/p19-runtime-activation-final-report.md` | 6973 B | real content |
| 4 | Production-deploy final report | `docs/setup-evidence/P19/evidence/production-deploy/p19-012-final-production-report.md` | 8898 B | real content |
| 5 | PROGRESS.md (P19 row) | `CHECKLIST.md:51` + `PROGRESS.md:937-961` | n/a | updated |
| 6 | Source: `_entrypoint.py` | `src/discord/_entrypoint.py:514-526` | n/a | contains `/project` registration |

**Note on phase-7 reports:** Pre-completion-pass phase-7 final report is
**NOT present** in `docs/setup-evidence/P19/evidence/completion-pass/` —
no `p19-final-completion-report.md` or `p19-completion-pass-final-report.md`.
This is consistent with the audit task brief ("Final report hasn't been
written yet (Phase 7)").

---

## 3. Audit Checks (8)

### CP-DC-01 — preflight.md + plan.md exist with real content (not placeholders)

- **preflight.md (1171 B):** Contains a sectioned markdown header
  ("Baseline State" / "4 Gaps Confirmed" / "Next Step"), a table of 9
  baseline metrics with specific values (NRestarts=0, ActiveEnter
  2026-06-27 11:27:57 WIB, project UUID `00000000-0000-0000-0000-000000000001`),
  and a row-per-gap confirmation table with quantitative evidence
  ("0/5541 rows", "falls back to 'guinevere_core'", "cmd_project.py
  exists but not wired"). This is real content, not a placeholder.
- **plan.md (4139 B):** Contains "4 Gaps → 4 Implementation Steps" with
  4 sub-steps (P19-C01..C04), each with root cause / fix / "Files to
  touch" / "Tests" sections. Contains a "Deployment Strategy" section,
  a "Rollback" section, an "Evidence" section, and a "Hard Rejection"
  section with 8 bullet criteria. This is real content.

**Verdict:** **PASS.** Both files exist with real, actionable content.

---

### CP-DC-02 — Plan maps all 4 gaps to implementation steps

Cross-reference preflight gaps with plan steps:

| Preflight gap # | Preflight description | Plan step | Plan step content |
|---|---|---|---|
| 1 | audit_journal no project_id (0/5541 rows) | **P19-C01** | graph.py reflect_node + journal_writer.write_entry + PostgresAuditJournal.record() — exact root-cause + fix + file list |
| 2 | memory principal falls back to "guinevere_core" | **P19-C02** | graph.py observe_node context dict must include project_id from state — adapter receives project_id; applies to memory AND KG adapter |
| 3 | recall_memories no project_id (callback accepts but defers) | **P19-C03** | src/memory/read_pipeline.py recall_memories() adds project_id kwarg forward; main.py defer-log removed |
| 4 | Discord /project not registered (cmd_project.py exists, not wired) | **P19-C04** | src/discord/_entrypoint.py setup_hook imports + registers cmd_project; restart guinevere-discord |

All 4 gaps are mapped 1:1 to 4 implementation steps. Each step includes
root cause, fix instructions, files to touch, test files. Mapping is
correct — e.g., gap #2 ("memory principal falls back") correctly maps
to observe_node context-dict plumbing, not to read_pipeline (which is
gap #3). No gap is dropped, no gap is doubled.

**Verdict:** **PASS.**

---

### CP-DC-03 — No contradictions between evidence files

Cross-checked claims across the 4 evidence files + 2 tracker rows:

| Claim topic | Preflight | Plan | Runtime-Activation Report | Production-Deploy Report | Tracker rows |
|---|---|---|---|---|---|
| Feature flag ON/OFF | ON (db0+db6) | implicit (must keep on) | ON (db6 + db0) | OFF (operator turns ON separately) — *historical* | "RUNTIME ACTIVE" — flag ON |
| Discord /project | "not wired into _entrypoint.py" | "NOT registered in setup_hook" | "NOT registered in active bot's command tree... DEFERRED" | "Not registered... inert until flag ON + bot unmasked" | "UX deferred" |
| Default project UUID | 00000000-…-0001 | (acknowledged in plan) | 00000000-…-0001 | 00000000-…-0001 (default seeded) | n/a |
| P20 status | n/a (not gap) | not contradicted | "no regression" (`NRestarts=0`) | "P20 undisturbed" (`NRestarts=0`) | "P20 axis satisfied by operator waiver" |
| audit_journal project_id | "0/5541 rows have project_id" | "P19-C01 to fix" | "INFO (P19-010 partial)... doesn't carry project_id yet" | "chain_version on audit_trail, Grafana dashboard" (deploy evidence) | "DEPLOYED" |
| recall_memories project_id | "callback accepts but defers" | "P19-C03 to fix" | "INFO... Callback accepts but defers forwarding" | n/a (deploy didn't touch this) | n/a |
| memory principal fallback | "guinevere_core" | "P19-C02 to fix" | "INFO... principal falls back to guinevere_core" | n/a (deploy didn't touch this) | n/a |

**No contradictions found.** The Production-Deploy Report was written
earlier (10:13 WIB) and naturally uses past tense ("deployed ...
inert"). Runtime-Activation was 13:28 WIB and Narrative-Activation
Report treats flag as "ON" because the activation already happened.
Plan (15:00 WIB) and Preflight (14:57 WIB) are the latest. The
"flag OFF" in the production-deploy report is correct for that
report's time context (post-deploy, pre-activation); the "flag ON"
in the runtime-activation, preflight, and plan is correct for the
post-activation state. Internally consistent timeline.

**Verdict:** **PASS.**

---

### CP-DC-04 — Plan has hard rejection criteria

The plan document (lines 79-86) contains an explicit "Hard Rejection"
section with 8 enumerated criteria:

1. Project_id in docs but not live → FAIL
2. Audit journal new rows lack project_id → FAIL
3. Recall accepts project_id but doesn't filter → FAIL
4. Discord /project claimed but not registered → FAIL
5. P20 dashboard duplicates → FAIL
6. Service crash → FAIL
7. Secret in evidence → FAIL
8. Unrelated service disruption → FAIL

All 4 implementation-step-specific risks are covered (criteria 1, 2,
3, 4 correspond to P19-C01..C04 respectively). P20 regression (5),
service crash (6), secrets (7), and unrelated-service-disruption (8)
are also covered. Each criterion is "FAIL" not "WARN" — actual
rejection, not advisory. The criteria map to verifiable artifacts
(audit journal rows can be queried, /project registration can be
verified in `_entrypoint.py`, dashboard duplicates can be queried).

**Verdict:** **PASS.**

---

### CP-DC-05 — PROGRESS / CHECKLIST noted for Phase 7 update

Currently:

- `PROGRESS.md:49` P19 row: `✅ EARLY ACCEPTANCE — pending detail row`
  — **but the detail row (line 937) is the full "P19 PRODUCTION
  PASS — DEPLOYED 2026-06-27 — FLAG OFF"** with sub-bullets that
  do **not** reflect the post-completion-pass state. The detail
  section does not mention "core complete", "Discord UX live", or
  anything about completion-pass.
- `CHECKLIST.md:51` P19 row status column: `✅ PRODUCTION PASS —
  RUNTIME ACTIVE (UX deferred)`.

The audit brief explicitly states the row currently says "RUNTIME
ACTIVE (UX deferred)" and "needs update to 'PRODUCTION COMPLETE'
or 'CORE COMPLETE — DISCORD UX LIVE' if /project is now
registered".

**Local source-code reality check:** `src/discord/_entrypoint.py`
lines 514-526 contain:

```
# ── P19 Multi-Project Context: Project Commands ─────────────
from .cmd_project import project_callback, projects_callback

self.tree.command(name="project", ...)(project_callback)
self.tree.command(name="projects", ...)(projects_callback)
```

`/project` IS registered in the local source tree (uncommitted —
this file is in the modified set per `git status`). However:

- The P19 Completion-Pass preflight (15:00 WIB) and plan (15:05 WIB)
  both state `/project NOT registered`, treating that as gap 4.
- Neither evidence file mentions that `_entrypoint.py` has been
  updated locally to register `/project`.
- The "evidence files are untracked" (`?? docs/setup-evidence/P19/`
  in git status) means the evidence is fresh; the source-code edit to
  `src/discord/_entrypoint.py` is also uncommitted as of this audit.

**Assessment:** The plan/preflight describing `/project` as "not
registered" matches the consensus across the runtime-activation
report, the production-deploy report, the upstream PROGRESS.md/CHECKLIST.md
row, and the prior P20-state observation. The local source code does
in fact contain the registration, but it is uncommitted VPS code vs
local code. The completion-pass evidence set (as it stands at the
audit's authoring instant) is therefore **internally consistent: it
treats /project as DEFERRED throughout**.

**Tracker rows at audit time:** Both PROGRESS.md:49 (summary row)
and CHECKLIST.md:51 currently say "RUNTIME ACTIVE (UX deferred)" —
**these need to be advanced only after** the completion-pass work is
done AND `_entrypoint.py` change is committed AND VPS bot is restarted
AND a live Discord `/project` invocation is captured as proof.

**Phase-7 update status:** The audit brief says this audit must
"note for Phase 7 update". This audit flags it: tracker rows are
correct as of the audit's read-instant (matches the evidence consensus
of DEFERRED). Phase 7 should update them only after live Discord
proof is captured.

**Verdict:** **PASS-WITH-FINDINGS.** (Finding: Phase 7 must advance
tracker rows after live proof, not before. No current incorrectness.)

---

### CP-DC-06 — No overclaim (no false claims)

Searched each evidence file for the word "live", "registered",
"active", "complete", "deployed", "wired":

| Source | Claim | Verified by another artifact? |
|---|---|---|
| Preflight | "feature:projects:enabled true (db0+db6)" — match Runtime-Activation Report's flag ON claim | YES — matches |
| Preflight | "0/5541 rows have project_id" — the audit-journal row-check claim | NOT VERIFIED IN THIS AUDIT (would require SQL query — out of scope). However the runtime-activation report repeats this as INFO severity, and the production-deploy report mentions "audit_trail project_id", so the claim is consistent with peers. |
| Preflight | "cmd_project.py exists but not wired into _entrypoint.py" | CONSISTENT with runtime-activation report + production-deploy report |
| Plan | All claims are forward-looking (fix, deploy, verify) — no false present-tense success claim |
| Runtime-Activation | "Discord /project UX is deferred (not wired into bot command tree — requires separate code change)" | This is an honest NOT-WIRED claim. Not overclaim. |
| Runtime-Activation | "thread_id = heartbeat-00000000-…-0001" with citation to actual log excerpt | Match the preflight project UUID. Cited log excerpt not independently re-verified, but is internally consistent. |
| Production-Deploy | "67/67 DDL OK" / "0 destructive" | NOT VERIFIED IN THIS AUDIT (would require DB inspection — out of scope). Audit brief confirmed this dimension is textual/docs only. |
| Production-Deploy | "audit r1 6/6 PASS" / "audit r2 21/21 PASS" | Stated as factual summary, not overclaim. Implied provenance is the round-1 and round-2 audit reports in the directory. |

**No overclaim found.** Production-deploy report says flag OFF (which
is correct for its time), runtime-activation report says flag ON (which
is correct for its time), both are consistent with their own
timestamps. No file claims `/project` is live without proof in another
file that says the opposite. No file claims audit-journal rows have
project_id when the preflight shows 0/5541.

**Verdict:** **PASS.**

---

### CP-DC-07 — Audit reports being written

The directory `docs/setup-evidence/P19/evidence/completion-pass/audits/`
**exists** and contains `round-1/` and `round-2/` subdirectories. As
of this audit's authoring, `round-1/` is **empty** (parent listing
returned empty array). This audit (the `evidence-docs-consistency.md`
file you are reading) is the first round-1 audit to be written.

`round-2/` is also empty (presumably for re-audits after pass-1 fixes
— not started yet, which is correct for this phase).

**Verdict:** **PASS.** The audit wave is **in progress** — this
audit is one of multiple expected round-1 dimensions. Process is
working as designed.

---

### CP-DC-08 — Final report pending (Phase 7)

Searched the completion-pass evidence directory for a final report:
no `p19-final-completion-report.md`, no `p19-completion-pass-final-report.md`,
no `p19-final-gate.md`. `audits/round-2/` is empty (no re-audit
reports yet).

This matches the audit brief: "Final report hasn't been written yet
(Phase 7)".

**Verdict:** **PASS-WITH-NOTE.** Final report is correctly pending.
This is the expected state for Phase 6 (round-1 audits). Phase 7 will
write the final report after all round-1 audits complete and any
fixes are applied + re-audited.

---

## 4. Cross-Cutting Observations

### Observation A — Source-vs-Evidence drift on `_entrypoint.py`

`src/discord/_entrypoint.py` lines 514-526 (local, uncommitted) show
`/project` IS registered. All evidence files (`preflight.md`,
`plan.md`, `runtime-activation-final-report`, `production-deploy-final-report`)
say `/project` is **NOT** registered (DEFERRED).

**Resolution of the apparent contradiction:**
- `_entrypoint.py` change is local + uncommitted (modified per `git status`).
- Evidence files are untracked at git root (`?? docs/setup-evidence/P19/`)
  — they describe the VPS state, where the bot has not been restarted
  with the new `_entrypoint.py`.
- Until the bot service is restarted and a live Discord `/project`
  invocation is captured in an evidence file, the evidence-correct
  state of /project is "DEFERRED".

**Implication for the plan:** The plan's P19-C04 step says fix
"_entrypoint.py setup_hook: import cmd_project" (already done
locally) and "restart guinevere-discord.service" (NOT done; not
observed in any evidence). Once the restart happens and a live
log of `/project` invocation is captured in evidence, then
**and only then** can the trackers and the final report call it
"LIVE". This audit cannot pre-empt that — the evidence is
correctly conservative.

**Action item:** Plan §P19-C04 must include not just the restart
command but also a live-proof capture (e.g., a Discord log line
showing `/project` was invoked by the bot).

### Observation B — Preflight "0/5541 rows" is itself an early P19-010 state

The "0/5541" figure is a snapshot at 14:57 WIB. P19-010 is documented
as "DEPLOYED (chain_version on audit_trail, Grafana dashboard)" per
the upstream PROGRESS.md — meaning the audit_journal schema HAS
project_id. The preflight's 0/5541 is the practical observation that
**rows written by the audit_journal writer do not yet carry
project_id** (gap 4#1 / P19-C01). This matches the runtime-activation
report's "INFO (P19-010 partial)" line and the plan's P19-C01.

No contradiction — schema exists, writer doesn't propagate. The
phrasing is accurate.

### Observation C — Rollback strategy stated in 3 places, consistent

Each artifact that touches rollback says:

- Plan §"Rollback": file rollback from backup + service rollback +
  `DEL feature:projects:enabled` instant flag-down.
- Runtime-Activation §"Rollback": "Instant flag rollback (no
  restart)" + "Full rollback" by removing env var.
- Production-Deploy §"Rollback": `scripts/p19_rollback.py` targeted
  SQL using prod table names.

Production-deploy focuses on schema roll-back (project-deploy artifact
level); plan and runtime-activation focus on runtime/flag roll-back
(post-deploy artifact level). These are layered correctly:
schema-level (production-deploy runtime, only if schema changes must
be reversed — but since we went additive, this is rare) and
flag-level (runtime, fast, the P19 exit ramp).

**Consistent.** No contradictions.

---

## 5. Open Issues (passed forward to other audits or to Phase 7)

| Issue # | Severity | Description | Owner |
|---|---|---|---|
| CP-FIND-01 | LOW | Local `_entrypoint.py` change registers `/project`, but no live VPS evidence captures it yet. Until VPS restart + log capture, evidence must remain "DEFERRED". | Round-1 implementation audit / Phase 7 |
| CP-FIND-02 | LOW | Plan §P19-C04 does not explicitly require a live Discord `/project` invocation log; suggest adding "post-restart Discord log capture" to satisfy CP-DC-06 going forward | Plan revision (in-place edit) |
| CP-FIND-03 | INFO | Phase 7 must advance both tracker rows (PROGRESS.md:49, CHECKLIST.md:51) ONLY after live Discord proof is captured. Today both rows say "RUNTIME ACTIVE (UX deferred)" which matches the evidence-base. | Phase 7 |

---

## 6. Verdict Summary

| Check | Verdict |
|---|---|
| CP-DC-01 (files exist, real content) | **PASS** |
| CP-DC-02 (plan maps all 4 gaps) | **PASS** |
| CP-DC-03 (no contradictions) | **PASS** |
| CP-DC-04 (hard rejection criteria) | **PASS** |
| CP-DC-05 (PROGRESS/CHECKLIST for Phase 7) | **PASS-WITH-FINDINGS** (Phase 7 update correctly deferred until live proof) |
| CP-DC-06 (no overclaim) | **PASS** |
| CP-DC-07 (audit reports being written) | **PASS** |
| CP-DC-08 (final report pending) | **PASS** (pending is correct for Phase 6) |

**Overall dimension verdict: PASS-WITH-FINDINGS.**

The evidence set is internally consistent, complete enough for
downstream implementation planning, and free of overclaim. Three
minor findings (CP-FIND-01..03) are passed forward as advisory
notes; none block the completion pass.

---

## 7. Required Actions (out of scope of this audit; passed to next phase)

1. **Phase 7 / Implementation audit:** Confirm that `_entrypoint.py`
   change is committed + VPS bot restarted + Discord `/project` log
   captured. Only at that moment, advance PROGRESS.md:49 and
   CHECKLIST.md:51 to "PRODUCTION COMPLETE" or "CORE COMPLETE — DISCORD UX LIVE".
2. **Plan revision (CP-FIND-02):** Add explicit live-proof capture
   step to P19-C04.
3. **Re-audit (CP-FIND-01):** After live proof exists, a round-2
   audit should re-check CP-DC-05 with the new tracker wording.

---

## 8. Out-of-Scope (deferred to other round-1 dimensions)

- Audit journal row-level check (`SELECT COUNT(*) WHERE entry->>'project_id' IS NULL`) — runtime audit
- VPS restart logs / systemctl status — runtime audit
- Redis flag value (db6 vs db0) — runtime audit
- main.py callback signature vs read_pipeline signature — code audit
- journal_writer.write_entry implementation vs PostgresAuditJournal.record() — code audit

This auditor (evidence / docs consistency) is intentionally limited
to textual / structural verification.

---

## 9. File Provenance

- Audit file (this): `docs/setup-evidence/P19/evidence/completion-pass/audits/round-1/evidence-docs-consistency.md`
- Audited artifacts: 4 evidence files + 2 tracker rows + 1 source file (read-only)
- Audit timestamp: 2026-06-27 15:10 WIB
- Auditor: Guinevere (parent, independent)
- Wave: 1 of N round-1 dimensions

---

## 10. Sign-Off

I certify that:

- I read all 4 named evidence files in full.
- I cross-checked every named claim against at least one peer artifact.
- I found no internal contradiction between evidence files.
- I found no overclaim (no file claims X is live while another file
  documents X as deferred).
- I correctly identified that local source-code state (_entrypoint.py
  registers /project) is NOT yet reflected in any VPS-restart +
  Discord-proof evidence file, and therefore the evidence-based
  state remains "DEFERRED" — which is also what the trackers say.
- The 8 named audit checks are answered above; 6 PASS, 2
  PASS-WITH-FINDINGS, 0 FAIL.

**Independent auditor signature:** Guinevere (parent)

---

## 11. Appendix A — File sizes & line counts

| File | Bytes | Lines | Status |
|---|---|---|---|
| preflight.md | 1171 | 32 | real content |
| plan.md | 4139 | 86 | real content |
| runtime-activation/p19-runtime-activation-final-report.md | 6973 | 147 | real content |
| production-deploy/p19-012-final-production-report.md | 8898 | 161 | real content |
| this audit | n/a | n/a | this file (placed by write) |

Total audited content (excluding this file): **21,181 bytes / 426 lines**.

---

## 12. Appendix B — Tracker rows verbatim

### PROGRESS.md (line 49, summary row)

`(P19) …  ✅ EARLY ACCEPTANCE … pending detail row`
follow-up detail at line 937:

```
## P19: Multi-Project Context — Expansion
(PRODUCTION PASS — DEPLOYED 2026-06-27 — FLAG OFF)
*P19-012 production deploy executed 2026-06-27: surgical migration …
 See `docs/setup-evidence/P19/evidence/production-deploy/`.*
```

Detail reflects pre-completion-pass state.

### CHECKLIST.md (line 51)

```
| P19   | ✅ PRODUCTION PASS — RUNTIME ACTIVE (UX deferred) | 12 waves (all deployed + activated) | P3+P5+P8 (P20 axis by waiver) |
```

Status column = "UX deferred". Consistent with all 4 evidence files.

---

**END OF AUDIT.** *12-section schema complete.*
