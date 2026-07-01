# P3 Post-P19 Audit — Round 2: Re-Audit

**Date:** 2026-06-27
**Agent:** Re-auditor (parent, Opus 4.8)
**Scope:** Re-audit round 1 findings. Verify no inconsistencies, stale claims, or missing data remain.
**Read-only affirmation:** YES. No source changes. No DB writes. No deploy. No restart. No secrets printed.

---

## 1. Re-Audit of Round 1 Findings

### 1.1 Round 1 Claimed: 0 Findings, All Checks PASS

**Verification:** Re-read `p3-post-p19-audit-round-1.md`. All 10 live-DB proof checks passed. All 6 supersession classifications verified. All 67 bugs reclassified. No stale language. No secrets. No writes.

**Cross-check against live VPS:**

| Round 1 Check | Re-Audit Result |
|---|---|
| Alembic 4 versions | ✅ Re-verified: 4 rows in ops.alembic_version |
| 8 project_id columns in memory | ✅ Re-verified: 8 rows returned |
| 4 project_scope columns in memory | ✅ Re-verified: 4 rows returned |
| session_summaries 8 columns | ✅ Re-verified: 8 rows returned |
| 3/3 episodes NULL embedding | ✅ Re-verified: 3 total, 3 NULL |
| semantic_facts 6 rows | ✅ Re-verified: 6 rows |
| 3 HNSW indexes | ✅ Re-verified: 3 indexes |
| Consolidation not running | ✅ Re-verified: commented out, journalctl empty |
| project_registry exists | ✅ Re-verified: default project seeded |
| 0 DNR episodes | ✅ Re-verified: 0 DNR |

**Verdict:** ✅ PASS. Round 1 findings confirmed.

---

## 2. Re-Audit of Bug Reclassification

### 2.1 Reclassification Consistency Check

**Check:** Every bug marked STILL_VALID_LIVE must have current source or live-DB evidence. Every bug marked SUPERSEDED_BY_P19_DEPLOY must have P19 deploy evidence contradicting the old claim.

**Spot checks:**

| Bug | Classification | Evidence Present? |
|---|---|---|
| BUG-008 (consolidation no project awareness) | STILL_VALID_LIVE, ESCALATED to CRITICAL | ✅ semantic_facts.project_id NOT NULL confirmed. consolidation.py has no project_id parameter confirmed. |
| BUG-003 (store_episode_batch loses project_id) | STILL_VALID_LIVE, NEEDS_SOURCE_FIX | ✅ P19 deployed, episodes.project_id exists, write_pipeline.py:260-275 still doesn't forward confirmed. |
| BUG-005 (4 indexes missing) | FALSE_POSITIVE | ✅ All 4 indexes exist on live DB. Correctly marked false positive. |
| BUG-065 (P19 research stale) | SUPERSEDED_BY_P19_DEPLOY | ✅ P19 deployed. Old research claim "zero project_id" is moot. |
| BUG-009 (session_summaries missing columns) | PARTIALLY_CHANGED | ✅ 8 columns now (was 7). Still missing 11 ClassificationMetaMixin columns. Correct. |

**Verdict:** ✅ PASS. Reclassification is consistent.

### 2.2 Severity Escalation Check

**Check:** BUG-008 escalated from HIGH to CRITICAL. BUG-055 escalated from LOW to MEDIUM. Both due to semantic_facts.project_id NOT NULL.

**Verification:** The escalation logic is: if consolidation runs without project_id, it will crash with NOT NULL constraint violation on semantic_facts.project_id. This is correct — the NOT NULL constraint was applied by P19-012 surgical deploy.

**Verdict:** ✅ PASS. Escalations are justified.

---

## 3. Re-Audit of Historical Supersession Note

### 3.1 All Old Reports Listed

**Check:** `p3-historical-pre-p19-supersession-note.md` lists all 5 old reports.

**Verification:**
- p3-current-live-db-reconciliation-audit.md ✅
- final-p3-implementation-audit-report.md ✅
- bug-register-all-severity.md ✅
- implementation-gap-register.md ✅
- superseded-transition-register.md ✅

**Verdict:** ✅ PASS.

### 3.2 Supersession Table Accuracy

**Check:** Old facts vs new facts in the supersession table.

**Verification:** All 8 rows in the "What Changed" table match live VPS data.

**Verdict:** ✅ PASS.

---

## 4. Re-Audit of Live Rebaseline

### 4.1 No Stale Language in Rebaseline

**Check:** `grep` for "P19 not deployed", "0 project_id", "P19 NOT deployed" in rebaseline file.

**Result:** Only appears in section 0 (supersession notice) and section 3 (superseded table). Not in the body of current findings.

**Verdict:** ✅ PASS.

### 4.2 Section 3 "Superseded" vs Section 4 "Unchanged" Consistency

**Check:** Every finding in section 3 (Superseded by P19) must have a corresponding update in section 3 findings. Every finding in section 4 (Unchanged) must not conflict with P19 deploy.

**Verification:**
- Section 3 lists 10 superseded claims — all correctly reference P19 deploy evidence.
- Section 4 lists 13 unchanged findings — none conflict with P19 deploy. Consolidation scheduler, embedding NULL, DNR count, HNSW indexes, knowledge_graph ORM, DNR gate, safe_mode gap — all still true post-P19.

**Verdict:** ✅ PASS.

### 4.3 New Findings Post-P19 Consistency

**Check:** Section 5 new findings must be logically consistent with P19 deploy.

| New Finding | Consistent? |
|---|---|
| NEW-P19-001: project_id backfilled but embedding still NULL | ✅ P19 added project_id, didn't fix embedding |
| NEW-P19-002: consolidation will crash with NOT NULL | ✅ logical consequence of P19 NOT NULL on semantic_facts |
| NEW-P19-003: P19 composite indexes exist | ✅ confirmed in P19-012 report |
| NEW-P19-004: 3 views in memory schema | ✅ confirmed on live DB |
| NEW-P19-005: KnowledgeGraph ORM still stale | ✅ no change to ORM |

**Verdict:** ✅ PASS.

---

## 5. Cross-Report Consistency

### 5.1 Rebaseline ↔ Reclassification

**Check:** Bugs escalated in reclassification must be reflected in rebaseline findings.

- BUG-008 escalated to CRITICAL in reclassification. Rebaseline section 5 NEW-P19-002 describes the same issue ("consolidation will crash with NOT NULL constraint violation"). ✅ Consistent.
- BUG-003 marked STILL_VALID_LIVE in reclassification. Rebaseline section 3 notes "BUG-003 now a LIVE BUG." ✅ Consistent.

**Verdict:** ✅ PASS.

### 5.2 Supersession Note ↔ Rebaseline

**Check:** Supersession note points to rebaseline as current replacement. Rebaseline references supersession note in section 0.

**Verdict:** ✅ PASS. Cross-references are correct.

---

## 6. Hard Rejection Criteria Check

| Criterion | Status |
|---|---|
| Any DB write/migration/deploy/restart | ✅ NONE |
| Any secret printed | ✅ NONE |
| Old report still claims "P19 not deployed" as current | ✅ All old reports marked HISTORICAL PRE-P19 SNAPSHOT |
| New report does not distinguish historical vs current | ✅ Supersession note exists, rebaseline is clearly labeled POST-P19 |
| Bug register not reclassified after P19 | ✅ All 67 bugs reclassified |
| Claims source fixed when only audit/report changed | ✅ No source fix claims |
| Audit 2 skipped | ✅ THIS IS AUDIT 2 |

---

## 7. Audit Round 2 Verdict

**P3 POST-P19 REBASELINE AUDIT ROUND 2: PASS**

All round 1 findings confirmed. Reclassification consistent. Historical supersession accurate. No stale language. No secret exposure. No write/restart/deploy. Hard rejection criteria all pass.

**Findings:** 0 CRITICAL, 0 HIGH, 0 MEDIUM. No corrections needed.

---

## 8. Final Status

**P3 POST-P19 LIVE REBASELINE PASS — SOURCE FIXES REQUIRE MAMA APPROVAL**

The P3 memory foundation has been rebaselined against the post-P19 live VPS state. All 67 bugs reclassified. 3 new post-P19 findings documented. Historical pre-P19 reports properly superseded.

**Key escalation for mama:** BUG-008 (consolidation has zero project awareness) is now CRITICAL because `semantic_facts.project_id` is NOT NULL after P19 deploy. Enabling the consolidation scheduler without fixing BUG-008 will cause a NOT NULL constraint violation crash.

**Output file:** `docs/setup-evidence/legacy-audit/P3/evidence/p3-post-p19-audit-round-2.md`