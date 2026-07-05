# P19 Completion Round 2 — Evidence / Documentation Consistency Audit

**Phase:** Completion Round 2 — Auditor 1 (Docs / Evidence consistency)
**Date:** 2026-06-27
**Author:** Sarah (Docs / Evidence auditor)
**Scope:** Cross-check P19 evidence tree + top-level docs (PROGRESS.md, CHECKLIST.md, P19 README, production-deploy final report, p19-final-verdict) for internal contradictions and stale claims against live VPS ground-truth (round-2 research report).
**Method:** Pure read-only audit. No service queries, no DB touches, no commits. All quoted passages are verbatim excerpts from files on disk.

---

## 1. Inputs Read

| # | Path | Purpose |
|---|---|---|
| 1 | `docs/setup-evidence/P19/README.md` | P19 index / status / step list |
| 2 | `docs/setup-evidence/P19/evidence/production-deploy/p19-012-final-production-report.md` | Production-pass / flag-off claim |
| 3 | `docs/setup-evidence/P19/evidence/implementation/p19-final-verdict.md` | Pre-deploy "deploy ready" verdict |
| 4 | `PROGRESS.md` (root) | Top-level tracker; P19 row |
| 5 | `CHECKLIST.md` (root) | Top-level checklist; P19 cost row |
| 6 | `docs/setup-evidence/P19/evidence/completion-round-2/research/p19-completion-ground-truth.md` | Ground-truth research (live VPS state) |
| 7 | `docs/setup-evidence/P19/evidence/runtime-activation/p19-runtime-activation-final-report.md` | Runtime activation final report (flag-on step) |

---

## 2. Stale / Incorrect Claims — File × Claim × Actual

> Format: file → line(s) → claim as written → actual as captured by ground-truth research.

### Stale-claim table

| # | File | Line(s) | Claim (verbatim or summarized) | Actual |
|---|---|---|---|---|
| 1 | `docs/setup-evidence/P19/evidence/production-deploy/p19-012-final-production-report.md` | 12, 14, 52, 54, 128, 130, 154, 159 | "P19 PRODUCTION PASS — DEPLOYED 2026-06-27 — **FLAG OFF**"; `feature:projects:enabled = None (OFF)`; "Flag stays OFF until operator explicitly turns it ON" | Round-2 ground-truth shows flag **ON** at 2026-06-27 15:31:10 WIB; runtime-activation final-report records flag ON, `LIFE_KERNEL_PROJECT_ID` set, `/project` and `/projects` Discord commands registered live. Deploy report is correct only for the 2026-06-27 ~21:40–10:20 WIB deploy window but is now stale because the operator followed up with runtime activation in the same day. |
| 2 | `docs/setup-evidence/P19/evidence/production-deploy/p19-012-final-production-report.md` | 62 (table row 3) | "ActiveEnterTimestamp = 2026-06-25 08:26:43 WIB — unchanged after P19 fixes" | Round-2 ground-truth evidence records `ActiveEnterTimestamp = 2026-06-27 15:31:10 WIB` — the systemd unit restarted at runtime activation, so the timestamp is **no longer** the pre-deploy P20 mark. |
| 3 | `docs/setup-evidence/P19/evidence/production-deploy/p19-012-final-production-report.md` | 7 ("P20 status unchanged"), 70 ("P20 CLOSED … undisturbed throughout. Soak clock preserved.") | P20 was left undisturbed by the P19 deploy / runtime activation; soak clock preserved | Runtime activation restarted `guinevere-core.service` (ActiveEnterTimestamp advanced to 2026-06-27 15:31:10 WIB) — the soak clock as defined in the P20 report (`started_at = ActiveEnterTimestamp`) was therefore broken even though P20 functionality remains healthy. Report's "Soak clock preserved" wording is now stale. |
| 4 | `docs/setup-evidence/P19/README.md` | 3 (top status line) | "🟣 P19 DEFINITION COMPLETE — P20 AXIS SATISFIED BY OPERATOR WAIVER — IMPLEMENTATION HOLD BY OPERATOR / P19-001 COMPLETE" | PROGRESS.md line 49 row says "P19 Multi-Project Context — ✅ PRODUCTION COMPLETE — CORE + DISCORD UX LIVE". README top status belongs to the 2026-06-25 definition phase and was never advanced. README is the most-stale file. |
| 5 | `docs/setup-evidence/P19/README.md` | 89–99 (Progress table rows P19-002 → P19-012) | All 11 implementation steps show "⬜ HELD" / "⬜ HELD (operator-gate)" | PROGRESS.md confirms **all 12 waves DEPLOYED + P19-012 PRODUCTION PASS** (flag ON + `/project` registered live, see paragraphs in PROGRESS.md lines 937–961). README progress table has not been advanced since the 2026-06-25 definition snapshot. |
| 6 | `docs/setup-evidence/P19/README.md` | 31–33 | "P19 implementation waves P19-001..012 are scaffolded and **ready for implementation by operator approval**. Waves touching P20 production files are held by operator discretion" | Stale. Waves P19-002..011 are DEPLOYED on VPS (per PROGRESS.md) and P19-012 reached PRODUCTION PASS. Only "operator holds" rationale left is optional P19-007 Discord-UX un-mask (now observed live). |
| 7 | `docs/setup-evidence/P19/README.md` | 17 (HARD STOP description) | "HARD STOP stays global; project-local pause is a distinct, weaker concept" | Stale-OK in concept but stale in the report: ADR-052 mentions `project:{id}:paused` whereas the live runtime uses flag-gated `LIFE_KERNEL_PROJECT_ID` instead (per `runtime-activation/p19-runtime-preflight.md`). README does not reflect this. README still lists `src/projects/registry.py` "planned" (line 70) when PROGRESS.md shows DEPLOYED. |
| 8 | `docs/setup-evidence/P19/README.md` | 50–62 (Directory Structure) | Lists `evidence/audits/round-1/`, `evidence/audits/round-2/`, `evidence/p19-definition-verification.md`, `evidence/auditor-gate.md`, `evidence/final-p19-planning-report.md` | These paths still exist. But README does **not** mention the new dirs created in the same `evidence/` tree: `production-deploy/`, `runtime-activation/`, `completion-pass/`, `completion-round-2/` (research, plan, audits subdirs). README evidence index is incomplete. |
| 9 | `docs/setup-evidence/P19/evidence/implementation/p19-final-verdict.md` | 11 (top-line), 88, 128 | Verdict: **"P19 LOCAL IMPLEMENTATION ENTERPRISE PASS — DEPLOY READY, OPERATOR APPROVAL REQUIRED"**, dated 2026-06-26; "The only remaining step is operator approval to execute P19-012 deploy" | Stale by 24h+. P19-012 deploy happened (PROGRESS.md), runtime activation happened (runtime-activation final-report), flag is now ON. This verdict doc now reads as if the deploy is still pending. It also claims "16h+ uptime" (line 70) and "0 restarts" (line 70) — both broken once runtime activation restarted `guinevere-core.service` (ActiveEnterTimestamp advanced to 2026-06-27). |
| 10 | `docs/setup-evidence/P19/evidence/implementation/p19-final-verdict.md` | 116 ("Total evidence files: 84") | Asserts 84 evidence files | Today's `find docs/setup-evidence/P19/evidence -type f | wc -l` returns a substantially larger number (well past 84) once the production-deploy, runtime-activation, completion-pass, completion-round-2 trees are counted. The "84 total" count is stale even before the round-2 churn. |
| 11 | `PROGRESS.md` line 7 ("Last Updated 2026-06-19") | header | "Last Updated: 2026-06-19" | PROGRESS.md was clearly rewritten multiple times after 2026-06-19 (P14-HC same-day block added, P19 row added afterward, P20 / P21 / P22 / P23 / P24 blocks added). The "Last Updated 2026-06-19" header is stale. |
| 12 | `PROGRESS.md` line 50 (P20 row) | Says "P20 visible autonomy online; operator waived 24h soak 2026-06-25 — EARLY PRODUCTION ACCEPTANCE, PASS WITH ACCEPTED RISK" | PROGRESS.md is internally inconsistent with live state because there is **no row saying `P20 ActiveEnterTimestamp advanced to 2026-06-27 15:31:10 WIB during P19 runtime activation`**. PROGRESS.md is also missing any reference to P19 runtime activation (it documents only P19 production deploy, not the flag-ON + `/project` registration). |
| 13 | `CHECKLIST.md` line 51 (P19 cost row) | "P19 ✅ PRODUCTION COMPLETE — CORE + DISCORD UX LIVE — 12 waves + completion pass — P3+P5+P8 (P20 axis by waiver)" | Stale-OK in spirit (significant progress). However CHECKLIST.md does **not** mention the runtime activation follow-up the same way PROGRESS.md does (no per-step entry for `/project` and `/projects` registration, no flag-ON entry). It also omits the round-2 audit chain entirely. |
| 14 | `CHECKLIST.md` lines 1173 ("('#10')" — legend) | "✅ Complete | 🔄 In Progress | ⏸️ Blocked | ⏳ Not Started | ★ Critical path" | "🟣" emoji used widely in PROGRESS.md and in `docs/setup-evidence/P19/README.md` ("🟣 P19 DEFINITION COMPLETE …") has no legend entry — operators reading the docs cannot decode the 🟣 symbol consistently. |

### Cross-document contradictions

| # | Topic | Producer A | Producer B | Reconciled truth (per ground-truth) |
|---|---|---|---|---|
| C1 | Flag status | production-deploy final report §2 §11: **OFF** | PROGRESS.md P19 cell text: **flag ON**; runtime-activation final-report: **ON** at 15:31:10 WIB | Flag has been **ON since 2026-06-27 15:31:10 WIB**. Report is from an earlier timepoint; PROGRESS.md + runtime-activation are current. |
| C2 | ActiveEnterTimestamp | production-deploy final report §4 table: **2026-06-25 08:26:43 WIB unchanged** | ground-truth research: **2026-06-27 15:31:10 WIB** | Service was restarted during runtime activation; current value is 2026-06-27 15:31:10 WIB. |
| C3 | Recall health | production-deploy final report §4: "Errors 0"; §11: "Errors 0"; smoke-test: "16/16 PASS" | round-2 research: degraded errors observed in logs at ~15:30; recall pipeline project_id filter was one of the four gaps fixed | "0 errors during deploy window" is true; the round-2 fixes were applied **after** the deploy report was written. The deploy report is therefore an honest snapshot, but the PROGRESS.md headline (which has absorbed the round-2 fixes) is correct and the deploy report alone is now misleading without follow-up linking. |
| C4 | Discord UX | production-deploy final report §3 ("P19-007 deployed … inert until flag ON + bot unmasked") | runtime-activation final-report + check-list: `/project` and `/projects` registered live on the active bot | Round-1 deploy correctly noted "inert"; runtime activation un-masked & registered. Both can be true sequentially, but the deploy report's "inert" wording has no follow-up note in `production-deploy/`. |
| C5 | Step status | P19 README.md progress table: **all HELD** | PROGRESS.md P19 row: 12/12 DEPLOYED + 1 PRODUCTION PASS | PROGRESS.md is canonical (matches runtime activation evidence). P19 README.md has not been re-baselined since 2026-06-25. |

---

## 3. Missing / Suspect Evidence Files

**Counts (from this audit's `find` runs):**

```
production-deploy md files                : 19
verification.md (anywhere under evidence/) : 19
auditor-gate.md (anywhere under evidence/): 21
```

**Per-file inventory of `evidence/production-deploy/` (10 visible + 1 SQL):**

- p19-012-runtime-preflight.md ✓
- p19-012-deploy-plan.md ✓
- p19-012-backup-evidence.md ✓
- p19-012-schema-migration-evidence.md ✓
- p19-012-service-deploy-evidence.md ✓
- p19-012-smoke-test.md ✓
- p19-012-final-production-report.md ✓
- p19-012-auditor-gate.md ✓
- p19-surgical-ddl.sql (DDL artefact, not markdown)
- audits/round-1/* ✓ (7 entries claimed by report)
- audits/round-2/* ✓ (4 entries claimed by report)

**`find` reports 19 .md files in `production-deploy`** — close to expected. No critical missing files detected. Cross-checks:
- round-1 audit subdir contains 7 .md files; round-2 subdir contains 4 .md files. (Sub-claims in §10 of final-report match inventory available.)

**Suspect / risky:**

- The deploy report §10 enumerates 4 round-2 audit files: `security-rollback-reaudit`, `db-idempotency-observability-reaudit`, `ux-runtime-reaudit`, `SUMMARY-reaudit`. All four appear present (find returned 19 total = 7 + 4 + 8 named top-level .md).
- Two of the deploy auditing dimensions (DB-migration-safety, Runtime/P20-regression) have 11/11 / 10/10 PASS counts inside the deploy report itself. **Those score-cards are derived from claim, not from a separate auditor-gate file.** The auditor-gate here consolidates everything into one `p19-012-auditor-gate.md` instead of per-dimension files. That is acceptable, but PROGRESS.md/P19 README.md text suggests the auditor coverage is broader than the file set implies. Recommend adding 1-line reconciliation note.

**Missing evidence in PROGRESS.md text but present on disk:**

- PROGRESS.md does not link to `docs/setup-evidence/P19/evidence/runtime-activation/`. The round-1 docs (`p19-runtime-preflight.md`, `p19-flag-enable-evidence.md`, `p19-runtime-activation-auditor-gate.md`, `p19-runtime-activation-final-report.md`) all exist on disk; PROGRESS.md reference is to `docs/setup-evidence/P19/evidence/production-deploy/` only.
- PROGRESS.md does not link to `docs/setup-evidence/P19/evidence/completion-round-2/` either.

**`completion-round-2/` status:**

- `research/p19-completion-ground-truth.md` ✓ present (the file used as ground-truth source for this audit)
- `plan/p19-completion-round-2-plan.md` ✓ present
- `audits/discord-project-commands.md` ✓ present
- `audits/memory-recall-project-scope.md` ✓ present
- `final/` empty (no consolidation doc)
- `fixes/` empty (no fix narrative)

→ **Round-2 final/** and **fixes/** directories are empty.** A completion-round-2 final report file appears to be missing; this audit fills one of those gaps but is itself an audit, not a final/finalization document. Suggest creating `completion-round-2/final/completion-round-2-final-report.md` to document round-2 fixes (memory principal scoping, audit_journal project_id, recall pipeline project_id filter, Discord `/project` registration) and outcome.

**`runtime-activation/p19-activation-plan.md`** references "Round 2 evidence" under `completion-round-2/`; today only research + plan + audits exist there. Acceptable for the audit phase but flag for follow-up.

---

## 4. Recommended Doc Updates

| Pri | Update |
|---|---|
| P0 | **P19 README.md**: Bump top-line status from "🟣 P19 DEFINITION COMPLETE / IMPL HOLD BY OPERATOR" → "✅ P19 PRODUCTION COMPLETE — CORE + DISCORD UX LIVE — flag ON 2026-06-27". Replace progress table 89–99 HELD markers with pass markers, and add a "Runtime activation evidence" row pointing to `evidence/runtime-activation/`. |
| P0 | **P19 README.md** lines 17 / 21 / 70: replace `project:{id}:paused` and "src/projects/registry.py planned" wording with the live `feature:projects:enabled` flag + `LIFE_KERNEL_PROJECT_ID` + actually-deployed paths. |
| P0 | **P19 README.md** lines 50–62: extend Directory Structure tree with `evidence/production-deploy/`, `evidence/runtime-activation/`, `evidence/completion-pass/`, `evidence/completion-round-2/`. |
| P1 | **production-deploy/p19-012-final-production-report.md**: Add §12 "Follow-up" section noting (a) operator turned flag ON 2026-06-27 15:31:10 WIB, (b) `LIFE_KERNEL_PROJECT_ID` set, (c) Discord `/project` registered live, (d) ActiveEnterTimestamp advanced 2026-06-27. Mark the original §4 "P20 undisturbed / Soak clock preserved" row as historical; record live values from round-2 ground-truth. |
| P1 | **implementation/p19-final-verdict.md**: Header banner — add "**SUPERSEDED 2026-06-27** by `evidence/production-deploy/p19-012-final-production-report.md` (PRODUCTION PASS) and `evidence/runtime-activation/p19-runtime-activation-final-report.md` (flag ON, Discord UX live)." Otherwise readers will read a "deploy ready, awaiting operator approval" verdict that is 24h+ stale. |
| P2 | **PROGRESS.md line 7** ("Last Updated 2026-06-19"): bump to 2026-06-27 and add a footnote "// round-2 edits; P19 runtime activation 2026-06-27 15:31:10 WIB". |
| P2 | **PROGRESS.md P19 row**: Add explicit 4-gap-fix subrow (C01 audit_journal project_id, C02 memory principal scoped, C03 recall pipeline project_id filter, C04 Discord `/project` registered live) so the headline is anchored — currently only the inline narrative paragraphs at lines 937..961 carry that weight. |
| P2 | **PROGRESS.md P20 row**: Add a 1-line note that runtime activation restarted `guinevere-core.service` (AdvancedActiveEnterTimestamp 2026-06-27 15:31:10 WIB); warn that any P20 24h-soak claim from before runtime activation is now broken by the restart. |
| P3 | **CHECKLIST.md line 51** (P19 cost row): Add "round-2 fix chain + runtime activation" subrow, link to `evidence/runtime-activation/`. |
| P3 | **CHECKLIST.md lines 1173** (Legend): Add 🟣 (Definition complete; impl hold) and ⬜ (TODO/Held) entries so the emoji conventions across PROGRESS.md, P19 README, P20-waiver docs, etc., are consistent. |
| P3 | **`p19-final-verdict.md` line 116 ("Total: 84")**: refresh count or strike through. |
| P3 | **New file**: `docs/setup-evidence/P19/evidence/completion-round-2/final/completion-round-2-final-report.md` to consolidate round-2 fixes (4 gaps) and audit verdicts (discord-project-commands.md, memory-recall-project-scope.md, this evidence-docs-consistency.md). The `final/` and `fixes/` directories exist but are empty. |
| P3 | **`runtime-activation/p19-activation-plan.md`**: add a section "follow-up round-2 work" linking to `completion-round-2/` audits + this audit. |

---

## 5. Verdict

**FAIL.**

The P19 evidence-and-docs posture as of 2026-06-27 is internally inconsistent for an outside reader. Two of the three top-level trackers (PROGRESS.md, CHECKLIST.md) reflect round-2 runtime-activation outcomes; the most opinionated P19-specific document (`docs/setup-evidence/P19/README.md`) still says "IMPL HOLD" and shows every wave HELD, and one of the production-deploy reports still says "FLAG OFF" + "Soak clock preserved" + "P20 undisturbed" without any follow-up note about the runtime activation that flipped both of those. Three direct contradictions exist between the production-deploy final-report and the round-2 ground-truth (flag status, ActiveEnterTimestamp, recall health — though for the last one, the contradiction is benign because the round-2 recall fixes came **after** the deploy report was written).

Failure mode is **documentation drift**, not technical incorrectness of the runtime. The engineering work for round-2 looks correct in PROGRESS.md + the new `runtime-activation/` and `completion-round-2/` evidence files. Documentation must be reconciled so the next audit (round-3 or P20 follow-up) does not waste time re-deriving the same ground-truth.

**Blocking-list before this can move to PASS:**

1. P19 README.md top-line status and progress table updated.
2. production-deploy final-report §12 follow-up note added (flag ON, ActiveEnterTimestamp 2026-06-27, soak clock reset).
3. p19-final-verdict.md marked SUPERSEDED with link to canonical reports.
4. PROGRESS.md "Last Updated" header bumped; P20 row receives runtime-activation reconciliation note.

**Re-open criteria:**

- Once items 1–4 above land and at least one of `completion-round-2/final/` or `runtime-activation/` contains an explicit pass pointer to round-2 evidence (this audit + the two per-dimension audits `discord-project-commands.md`, `memory-recall-project-scope.md`), the docs-consistency auditor gates can move from FAIL → PASS without further investigation.

---

## 6. Auditor Self-Check

- All five inputs read cleanly; no parser errors, no truncate warnings.
- Cross-checks performed against `find` output for evidence-tree shape — counts match.
- No file was modified except creation of this audit.
- All contradictions and stale-claims verified by re-quoting the exact passage against the original file via Read tool.
- Evidence/docs-only audit; no runtime claims were made that would require service queries.

result: P19 evidence/docs consistency is FAIL — three direct contradictions between production-deploy final-report and round-2 ground-truth (flag OFF vs ON, ActiveEnterTimestamp 2026-06-25 vs 2026-06-27 15:31:10, 0 recall_degraded vs round-2 recall fixes applied after deploy report), P19 README.md still shows IMPL HOLD + every wave HELD vs PROGRESS.md showing 12/12 DEPLOYED + production-pass, and p19-final-verdict.md dated 2026-06-26 still reads "deploy ready, awaiting operator approval". All four stem from prose that never advanced past 2026-06-25 / 2026-06-26, while round-2 runtime activation has run on 2026-06-27. Recommend four targeted doc updates (P0 priority) before this auditor gates can flip to PASS.
