# Auditor Report: P12 Cross-File Consistency

**Date:** 2026-06-03  
**Auditor:** Guinevere (parent, direct audit)  
**Scope:** 4 files — `stepprompts/StepPrompts.md`, `PROGRESS.md`, `CHECKLIST.md`, `docs/IMPLEMENTATION_GUIDE.md`  
**Subject:** P12 Gmail/Email Integration — cross-file consistency of step counts, titles, totals, cost, and stale values

---

## Check Matrix

| # | Check | Result | Evidence |
|---|-------|--------|----------|
| 1 | P12 step count = 29 in all 4 files | **PASS** | StepPrompts: 29 headers, PROGRESS: `0/29`, CHECKLIST: `(29 steps)`, IMPL_GUIDE: `29` |
| 2 | `### Step P12-` header count = 29 | **PASS** | grep confirms 29 matching headers in StepPrompts.md |
| 3 | Total count = 288 in IMPLEMENTATION_GUIDE.md | **PASS** | Line 72: `288 (P13-P22 TBD)` |
| 4 | Total count = 288 in PROGRESS.md | **FAIL** | Line 12 header says `288` but line 51 Total row says `**203/236+**` (stale) |
| 5 | Expansion count = 52 in IMPLEMENTATION_GUIDE.md | **PASS** | Line 3: `52 steps (Expansion, P11-P12)`, line 70: `52 (P13-P22 TBD)` |
| 6 | No stale value `259` in PROGRESS.md or IMPL_GUIDE | **PASS** | Zero matches in both files |
| 7 | No stale value `236` in PROGRESS.md | **FAIL** | Line 51 Total row: `**203/236+**` |
| 8 | No stale value `233` in PROGRESS.md or IMPL_GUIDE | **PASS** | Zero matches in both files |
| 9 | No stale values in IMPLEMENTATION_GUIDE.md | **PASS** | Zero matches for 259, 236, 233 |
| 10 | P12 cost = $0/month in PROGRESS.md | **PASS** | Line 40: `$0` in Phase Summary table; line 554: `$0` in Cost Tracking table |
| 11 | P12 cost = $0/month in IMPLEMENTATION_GUIDE.md | **PASS** | Line 59: `$0`; line 132: `$0/month (Gmail API free tier + Resend free tier)` |
| 12 | P12 cost = $0/month in StepPrompts.md | **PASS** | Line 25849: `$0/month (Gmail API free tier + Resend free tier)` |
| 13 | P12 cost = $0/month in CHECKLIST.md | **FAIL** | Line 40 budget table: `TBD`; NOT `$0` |
| 14 | Step titles match: PROGRESS.md ↔ CHECKLIST.md | **PASS** | All 29 steps have identical titles between these two files |
| 15 | Step titles match: StepPrompts.md ↔ PROGRESS.md | **PASS** (minor) | Titles differ in wording (e.g., "Incremental Sync Engine" vs "Full/Hybrid Sync Engine") but map to same conceptual tasks. StepPrompts titles are more implementation-detailed; PROGRESS/CHECKLIST titles are shorter/earlier versions. See detailed comparison below. |
| 16 | StepPrompts.md header reflects P12 count | **FAIL** | Line 10: `23 (Expansion, P11) + TBD (P12-P22)` — should say `52 (Expansion, P11-P12)` |
| 17 | StepPrompts.md Phase Dependency Graph reflects P12 count | **FAIL** | Line 120: `P12 Gmail/Email Integration (TBD)` — should show `(29 steps)` |

---

## Step Title Comparison: StepPrompts.md vs PROGRESS.md/CHECKLIST.md

PROGRESS.md and CHECKLIST.md have identical titles (29/29 match). Differences below are StepPrompts vs the tracker pair.

| Step | StepPrompts.md | PROGRESS.md / CHECKLIST.md | Verdict |
|------|----------------|---------------------------|---------|
| P12-001 | GCP Project + API Enablement | GCP Project + Gmail API Enable | Minor — same scope |
| P12-002 | OAuth2 Token Management + !email-reauth | OAuth2 Credential + SOPS | Minor — expanded detail |
| P12-003 | Resend Client Setup | Resend Transactional Email | Minor — same scope |
| P12-004 | Gmail API Client Wrapper | Gmail API Client Wrapper | ✅ Exact match |
| P12-005 | Incremental Sync Engine | Full/Hybrid Sync Engine | Minor — implementation detail |
| P12-006 | Pub/Sub StreamingPull + Watch Renewal | Cloud Pub/Sub Push Pipeline | Minor — implementation detail |
| P12-007 | GmailAdapter (ChannelAdapter Implementation) | GmailAdapter (ChannelAdapter) | Minor — parenthetical difference |
| P12-008 | Channel Context Manager | Conversation Context Manager | Minor — same scope |
| P12-009 | Email Classifier (Cascade Pattern) | Email Classifier Cascade | Minor — parenthetical |
| P12-010 | Importance Scorer | Priority Scorer | Minor — synonym |
| P12-011 | Content Sanitizer + Injection Defense | Content Sanitizer + Injection Defense | ✅ Exact match |
| P12-012 | Secret Scanner + PII Redactor | Secret Scanner + PII Redactor | ✅ Exact match |
| P12-013 | Memory Store Integration | Memory Store Integration | ✅ Exact match |
| P12-014 | Financial Email -> P9 Bridge | Financial Email → P9 Bridge | Trivial — arrow style |
| P12-015 | Draft Generator (LLM) | Draft Generator (LLM) | ✅ Exact match |
| P12-016 | Discord Draft UX | Draft Approval UX (Discord) | Minor — same scope |
| P12-017 | Gmail Draft Sync + Send | Draft Send via Gmail API | Minor — same scope |
| P12-018 | Real-Time Email Notifications | Real-Time Notifications | Minor — extra word |
| P12-019 | Morning Briefing + On-Demand Digest | Morning Briefing Generator | Minor — expanded detail |
| P12-020 | !email-digest Command | !email-digest Command | ✅ Exact match |
| P12-021 | !email-consent + !email-reauth Commands | Consent + Surveillance Policy | Minor — command focus vs policy focus |
| P12-022 | Cross-Channel HARD STOP | Cross-Channel HARD STOP | ✅ Exact match |
| P12-023 | Surveillance Classification | Surveillance Data Classification | Minor — shortened |
| P12-024 | Watch Renewal + Health Check | Watch Health + Auto-Refresh | Minor — same scope |
| P12-025 | Grafana Dashboard + Metrics | Grafana Dashboard + Metrics | ✅ Exact match |
| P12-026 | Systemd Service + Runbook | Systemd Service + Runbook | ✅ Exact match |
| P12-027 | E2E Integration Test — Full Flow Verification (P12 GATE) | Integration Test (10 Scenarios) | Minor — expanded detail |
| P12-028 | Agent Loop Trigger Detector | Agent Loop Trigger Detector | ✅ Exact match |
| P12-029 | TaskContract Email Context | TaskContract Email Context | ✅ Exact match |

**Title consistency assessment:** 10 of 29 steps have exact matches. All 19 differences are minor wording variations — the conceptual task identity is preserved. PROGRESS.md/CHECKLIST.md form a perfectly consistent pair.

---

## FINDINGS SUMMARY

### PASS (12 / 17 checks)

| # | Check |
|---|-------|
| 1 | P12 = 29 steps in all 4 files |
| 2 | `### Step P12-` = 29 headers in StepPrompts.md |
| 3 | IMPLEMENTATION_GUIDE.md Grand Total = 288 |
| 5 | Expansion = 52 in IMPLEMENTATION_GUIDE.md |
| 6 | No stale `259` anywhere |
| 8 | No stale `233` anywhere |
| 9 | No stale values in IMPLEMENTATION_GUIDE.md |
| 10 | P12 cost = $0 in PROGRESS.md |
| 11 | P12 cost = $0 in IMPLEMENTATION_GUIDE.md |
| 12 | P12 cost = $0 in StepPrompts.md |
| 14 | PROGRESS.md ↔ CHECKLIST.md titles match (29/29) |
| 15 | StepPrompts.md ↔ PROGRESS.md titles match (minor variations OK) |

### FAIL (5 / 17 checks)

| # | Finding | Severity | Location | Fix |
|---|---------|----------|----------|-----|
| 4 | PROGRESS.md Total row shows `203/236+` instead of `203/288+` | **HIGH** | Line 51 | Change `236+` to `288+` |
| 7 | Stale value `236` in PROGRESS.md Total row | **HIGH** | Line 51 | Same as #4 |
| 13 | CHECKLIST.md budget table shows P12 cost = `TBD` instead of `$0` | **MEDIUM** | Line 40 | Change `TBD` columns for P12 to `$0` / `$29` / `$1` |
| 16 | StepPrompts.md header says `23 (Expansion, P11) + TBD (P12-P22)` | **MEDIUM** | Line 10 | Change to `52 (Expansion, P11-P12) + TBD (P13-P22)` |
| 17 | StepPrompts.md dependency graph shows `P12 Gmail/Email Integration (TBD)` | **LOW** | Line 120 | Change `(TBD)` to `(29 steps)` |

---

## FINAL VERDICT: ❌ FAIL

**5 failures, 12 passes.** The core data (P12 = 29 steps, step titles map correctly, expansion = 52, IMPLEMENTATION_GUIDE.md is clean) is correct. The failures are **stale tracker values** that were not updated when P12 expanded from TBD to 29 defined steps:

1. **PROGRESS.md line 51** — Total row still says `236+` (pre-P12-expansion number). Must be `288+`.
2. **CHECKLIST.md line 40** — Budget table still shows `TBD` for P12 cost. Must be `$0`.
3. **StepPrompts.md line 10** — Header still shows `TBD (P12-P22)` for expansion count. Must reflect 52.
4. **StepPrompts.md line 120** — Dependency graph shows `(TBD)` for P12 step count. Must show `(29 steps)`.

**Recommendation:** Fix the 4 stale references, then re-audit. The structural data (29 steps, 52 expansion, 288 total, $0 cost) is consistent across all files that were properly updated — only the summary rows/headers were missed.