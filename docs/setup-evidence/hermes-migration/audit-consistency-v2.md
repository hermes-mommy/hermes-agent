# Audit Report — Hermes Migration Consistency v2

> **Date**: 2026-06-04 | **Auditor**: Guinevere (Sisyphus-Junior)
> **Scope**: Re-audit after v1.1 phase duration fix — cross-check batch plan, 8 phase files, ADR-035
> **Previous audit**: NEEDS REVIEW (phase duration mismatch) → FIXED in summary table
> **Files audited**: 10 (batch-plan-migration.md + 8 phase-*.md + ADR-035-hermes-migration.md)

---

## Check Results

### Check 1: Phase durations — summary table vs ADR-035 Summary

**Verdict: PASS**

Batch plan summary table (lines 51-61) and ADR-035 Summary (lines 1181-1191) match exactly:

| Phase | Batch Plan | ADR-035 | Match |
|---|---|---|---|
| 0 | 2-3 days | 2-3 days | OK |
| 1 | 7-10 days | 7-10 days | OK |
| 2 | 5-8 days | 5-8 days | OK |
| 3 | 4-5 days | 4-5 days | OK |
| 4 | 5-7 days | 5-7 days | OK |
| 5 | 2-3 days | 2-3 days | OK |
| 6 | 1 day | 1 day | OK |
| 7 | 2-3 days | 2-3 days | OK |
| Total | 35-50 days | 35-50 days | OK |

---

### Check 2: Phase durations — batch plan section headers vs phase detail files

**Verdict: NEEDS REVIEW**

The summary table was fixed in v1.1, but per-phase section **headers** inside the batch plan body still carry old durations:

| Phase | Batch Plan Header | Summary Table | Phase File | Status |
|---|---|---|---|---|
| 0 | "1-2 days" (line 326) | 2-3 days | 2-3 days | RESIDUAL MISMATCH |
| 1 | "4-6 days (7-10 solo-dev)" (line 499) | 7-10 days | 7-10 days | OK (acknowledges both) |
| 2 | "4-6 days" (line 722) | 5-8 days | 5-8 days | RESIDUAL MISMATCH |
| 3 | "3-4 days" (line 995) | 4-5 days | 4-5 days | RESIDUAL MISMATCH |
| 4 | "3-4 days" (line 1126) | 5-7 days | 5-7 days | RESIDUAL MISMATCH |
| 5 | "2-3 days" (line 1256) | 2-3 days | 2-3 days | OK |
| 6 | "1 day" (line 1371) | 1 day | 1 day | OK |
| 7 | "2-3 days" (line 1479) | 2-3 days | 2-3 days | OK |

**Evidence**: Phases 0, 2, 3, 4 section headers retain pre-fix durations. The summary table + phase files are authoritative. Section headers should be updated.

**Also noted**: The dependency graph ASCII art (lines 238-282) retains old durations (Phase 0: 1-2d, Phase 1: 4-6d, Phase 2: 4-6d, Phase 3: 3-4d, Phase 4: 4-6d). These should be updated.

---

### Check 3: Phase ordering 0-1-2-3-4-5-6-7

**Verdict: PASS**

All 10 files use identical phase ordering. Dependency graph consistent across batch plan, ADR-035, and all phase files.

---

### Check 4: 5 architectural pillars

**Verdict: PASS**

| Pillar | Batch Plan | ADR-035 | Phase Files | Match |
|---|---|---|---|---|
| Discord | MIGRATE | MIGRATE | MIGRATE | OK |
| Memory | HYBRID | HYBRID | HYBRID | OK |
| Safety | HOOKS+PLUGINS | HOOKS+PLUGINS | HOOKS+PLUGINS | OK |
| MCP | HYBRID | HYBRID | HYBRID | OK |
| LLM | RETAIN 9Router | RETAIN 9Router | RETAIN 9Router | OK |

All 5 pillars consistently described. localhost:20128 confirmed for 9Router.

---

### Check 5: Code reduction — 31.2% net / 44.2% affected

**Verdict: PASS**

| Metric | Batch Plan | ADR-035 | Match |
|---|---|---|---|
| Net reduction | 31.2% (8,057 lines) | 31.2% (8,057 lines) | OK |
| Affected reduction | Not explicit | 44.2% (line 1173) | Minor (batch plan doesn't state 44.2%) |
| Pre-migration lines | 25,796 | 25,796 | OK |
| Post-migration lines | ~17,739 | ~17,739 | OK |
| Files eliminated | 20 | 20 | OK |

The 44.2% affected-code reduction is stated in ADR-035 but not explicitly in the batch plan. The batch plan does mention "Files refactored: 66 files" and "Files preserved verbatim: 27 files" which aligns numerically. Minor note — batch plan could quote 44.2% for completeness.

---

### Check 6: Timeline — 35-50 days total

**Verdict: PASS**

- Batch plan line 63: "Solo-developer realistic timeline: 35-50 days per ADR-035 v1.2"
- ADR-035 line 1191: "Total (realistic): 35-50 days"
- Day-50 decision gate described identically in both documents.
- Cumulative day range in summary table: 28-40 days (engineering) vs 35-50 days (realistic) — both documented.

---

### Check 7: 35 slash commands

**Verdict: PASS**

All files consistently reference 35 slash commands:
- Batch plan: Phase 2 gate "All 35 slash commands functional"
- ADR-035: Complete migration table covers all 35 commands (8 HIGH + 15 MEDIUM + 12 LOW)
- Phase-2-discord.md: Full table of 35 commands with plugin filenames
- Categories (8/15/12) consistent across all sources.

---

### Check 8: Hermes hooks count

**Verdict: NEEDS REVIEW**

The batch plan has an internal inconsistency:

- **Line 45** (Pillars summary): "7 lifecycle hooks" — CORRECT
- **Line 241** (Option D description): "6 Hermes hooks: pre_prompt, post_prompt, pre_tool_call, post_tool_call, pre_response, on_error" — INCORRECT, misses post_response

The actual 7 hooks:
1. pre_prompt — HARD STOP + distress
2. post_prompt — drift detection
3. pre_tool_call — consent gate + auth
4. post_tool_call — output sanitization
5. pre_response — final safety check
6. post_response — yandere + secrets + forbidden
7. on_error — error classification

ADR-035 and Phase-1-safety.md both document all 7 hooks correctly. Phase 1 implementation steps (1.2-1.8) create all 7. Line 241 of batch plan miscounts.

**Fix**: Line 241 should read "7 Hermes hooks" and include post_response.

---

### Check 9: AC-SAFE-001..008 — numbering and criteria mapping

**Verdict: FAIL**

The three documents map AC-SAFE numbers to **different criteria**. This is the most significant finding:

| AC-SAFE | Batch Plan (lines 649-659) | ADR-035 (lines 1669-1678) | Phase-1-Safety (lines 692-701) |
|---|---|---|---|
| 001 | HARD STOP | Safe-word neutral mode | HARD STOP 100% SLO |
| 002 | Yandere (Y6 impossible) | Time-to-neutral p99 <= 5s | Yandere Boundary |
| 003 | Consent (fail-closed) | Safe-word stops persona/surveillance | Consent Revocation |
| 004 | Distress (D0-D4) | D3/D4 false negatives = zero | Data Classification |
| 005 | DNR enforcement | Y5/Y6 zero restricted contexts | Memory Privacy |
| 006 | Secret scanner | Forbidden patterns blocked | Punishment Overflow |
| 007 | Drift detector | Safe-word logs minimal | Drift Detection |
| 008 | Forbidden patterns (shared w/ 006) | Crisis handling suspends persona | Surveillance No Confrontation |

**Three different mappings.** ADR-035 is the authoritative source (it's the Architecture Decision Record). The batch plan and phase-1-safety.md must align with ADR-035's mapping. This is a blocking inconsistency because AC-SAFE references appear in Go/No-Go criteria, gate descriptions, and safety checkpoints.

**Examples of conflict:**
- Batch plan maps AC-SAFE-002 to Yandere; ADR-035 maps it to time-to-neutral
- Phase-1 maps AC-SAFE-004 to Data Classification; ADR-035 maps it to D3/D4 distress
- Batch plan maps AC-SAFE-006 to Secrets/Punishment; ADR-035 maps it to Forbidden patterns

**Recommendation**: Normalize all files to ADR-035's authoritative AC-SAFE mapping (lines 1669-1678).

---

### Check 10: Service names consistency

**Verdict: NEEDS REVIEW**

The batch plan v1.1 revision history notes "guinevere-bot→guinevere-discord, removed guinevere-core, service count 8→7." However, **ADR-035 itself** still uses legacy service names:

| ADR-035 Line | Legacy Name | Should Be | Context |
|---|---|---|---|
| 1364 | guinevere-bot | guinevere-discord | Phase 2 rollback |
| 1375 | guinevere-bot | guinevere-discord | Global rollback |
| 1389 | guinevere-core | (removed service) | Global rollback — non-existent |
| 1395 | guinevere-bot | guinevere-discord | Rollback verification |
| 1210 | guinevere-bot | guinevere-discord | Universal kill-switch |

All 8 phase files and the batch plan use the correct guinevere-discord name. ADR-035 was not updated during the v1.1 fix pass.

**Additionally**: ADR-035 line 1389 references guinevere-core.service which was documented as removed (service count corrected from 8→7). This service no longer exists.

---

### Check 11: Port numbers

**Verdict: PASS**

| Service | Port | Batch Plan | ADR-035 | Phase Files |
|---|---|---|---|---|
| PostgreSQL | 5433 | OK | OK | OK |
| Redis | 6380 | OK | OK | OK |
| 9Router | 20128 | OK | OK | OK |
| Core health | 8000 | OK | OK | OK |
| Hermes metrics | 9191 | OK | OK | OK |

All consistent.

---

### Check 12: Risk levels per phase

**Verdict: PASS**

| Phase | Batch Plan | ADR-035 | Phase File |
|---|---|---|---|
| 0 | LOW | LOW | LOW |
| 1 | HIGH | HIGH | HIGH |
| 2 | HIGH | HIGH | HIGH |
| 3 | MEDIUM | MEDIUM | MEDIUM |
| 4 | MEDIUM | MEDIUM | MEDIUM |
| 5 | LOW | LOW | LOW |
| 6 | LOW | LOW | LOW |
| 7 | LOW | LOW | LOW |

---

### Check 13: Gate criteria — batch plan vs phase files

**Verdict: PASS**

Per-phase gate criteria match between batch plan "Gate Criteria" subsections and each phase file's "Gate Criteria" table. All 8 phases verified. Minor wording differences (e.g., "clean" vs "all PASS") are semantically equivalent.

---

### Check 14: Rollback procedure consistency

**Verdict: PASS** (with service-name caveat from Check 10)

Core rollback commands are consistent:
- Universal kill-switch: hermes gateway stop — identical everywhere
- Per-phase rollback commands match between batch plan and phase files
- ADR-035 rollback table aligns with phase file procedures

**Caveat**: ADR-035 rollback commands use guinevere-bot instead of guinevere-discord (see Check 10).

---

### Check 15: Shadow mode — 4-stage description

**Verdict: PASS**

| Element | Batch Plan | Phase-2-Discord | ADR-035 |
|---|---|---|---|
| Minimum duration | 48hr+ | 48hr+ (staged) | 48 hours |
| Stage breakdown | 4 stages (implicit) | 4 stages explicit | Summarized |
| Active injections | 5 types, 9 tests | Same 5 types, 9 tests | Same 5 types |
| Cost cap | $5 | $5 | $5 |

Active safety injections (3× HARD STOP, 3× Y6, 1× consent, 1× distress, 1× hook failure) identical across all files.

---

### Check 16: ADR-035 cross-references

**Verdict: PASS**

All 12 ADR references in ADR-035 verified to exist in adr/ directory and adr/README.md: ADR-001, ADR-002, ADR-003, ADR-005, ADR-007, ADR-013, ADR-022, ADR-025, ADR-029, ADR-030, ADR-032, ADR-033. All document path references resolvable.

---

## Summary

| # | Check | Verdict |
|---|---|---|
| 1 | Phase durations: summary table vs ADR-035 | PASS |
| 2 | Phase durations: section headers vs phase files | NEEDS REVIEW |
| 3 | Phase ordering 0-1-2-3-4-5-6-7 | PASS |
| 4 | 5 architectural pillars | PASS |
| 5 | Code reduction: 31.2% / 44.2% | PASS |
| 6 | Timeline: 35-50 days | PASS |
| 7 | 35 slash commands | PASS |
| 8 | Hermes hooks count | NEEDS REVIEW |
| 9 | AC-SAFE-001..008 numbering/mapping | FAIL |
| 10 | Service names consistency | NEEDS REVIEW |
| 11 | Port numbers | PASS |
| 12 | Risk levels per phase | PASS |
| 13 | Gate criteria | PASS |
| 14 | Rollback procedures | PASS |
| 15 | Shadow mode 4-stage | PASS |
| 16 | ADR-035 cross-references | PASS |

---

## Final Verdict: NEEDS REVIEW

**Rationale**: One FAIL (Check 9 — AC-SAFE mapping is materially inconsistent between documents, with three different mappings in batch plan, ADR-035, and phase-1-safety.md) plus three NEEDS REVIEW findings. The AC-SAFE inconsistency is the blocking item — it affects safety gate references, Go/No-Go criteria, and acceptance criteria numbering across the entire migration plan.

### Recommended Fixes

1. **AC-SAFE mapping (Check 9 — CRITICAL)**: Normalize batch plan and phase-1-safety.md to use ADR-035's authoritative AC-SAFE mappings (lines 1669-1678). Update the safety checkpoint table in batch plan (lines 646-659) and the AC-SAFE table in phase-1-safety.md (lines 692-701).

2. **Section headers (Check 2)**: Update batch plan section headers for Phases 0, 2, 3, 4 to match summary table and phase file durations. Also update the ASCII dependency graph (lines 238-282).

3. **Hook count (Check 8)**: Fix batch plan line 241 to read "7 Hermes hooks" and include post_response.

4. **Service names (Check 10)**: Update ADR-035 legacy guinevere-bot references to guinevere-discord and remove references to deleted guinevere-core service.

---

## Appendix: File Inventory

| # | File | Lines | Status |
|---|---|---|---|
| 1 | batch-plan-migration.md | 2,036 | Active v1.1 |
| 2 | phase-0-security.md | 413 | Active |
| 3 | phase-1-safety.md | 923 | Active |
| 4 | phase-2-discord.md | 482 | Active |
| 5 | phase-3-memory.md | 487 | Active |
| 6 | phase-4-mcp.md | 449 | Active |
| 7 | phase-5-skills.md | 406 | Active |
| 8 | phase-6-llm.md | 454 | Active |
| 9 | phase-7-hardening.md | 611 | Active |
| 10 | ADR-035-hermes-migration.md | 2,512+ | Accepted v1.2 |