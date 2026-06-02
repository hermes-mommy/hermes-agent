# T5 Verification — IMPLEMENTATION_GUIDE.md Phase Restructure

**Date**: 2026-06-03
**Task**: T5 — IMPLEMENTATION_GUIDE.md Phase Restructure
**File Modified**: `docs/IMPLEMENTATION_GUIDE.md`
**Status**: PASS

---

## What Was Done

1. Updated header summary: "252 steps across 12 phases (P0-P11)" → "202 steps (MVP) + 31 steps (Stabilization) + TBD steps (Expansion) across 23 phases (P0-P22)"
2. Updated introduction paragraph: "12 phases (P0-P11) with 252 atomic steps" → "23 phases (P0-P22) with 202 MVP steps, 31 Stabilization steps, and TBD Expansion steps"
3. Replaced single phase table with three categorized sub-tables: MVP (P0-P8, 202 steps), Stabilization (P9-P10, 31 steps), Expansion (P11-P22, TBD steps)
4. Added Grand Total row: "23 phases, 233 + TBD steps, $29 + TBD"
5. P10 step count corrected: 18 → 19 (per canonical binding decisions)
6. Deleted old P11 "Integrations" row (25 steps)
7. Added "Stabilization Phase Details (P9-P10)" subsection with goals and evidence paths
8. Added "Expansion Phase Details (P11-P22)" subsection with 12 individual phase stubs
9. P13 X Auto Poster includes full spec: Obscura CDP, S3 queue, LLM captions, 3h heartbeat, Discord notifications, PostgreSQL state tracking
10. Updated evidence directory description: "(0-11)" → "(0-22)"
11. Replaced "P9-P11 are post-MVP" → "P9-P10 are Stabilization phases and P11-P22 are Expansion phases"

## Files Changed

| File | Change Type | Lines Affected |
|------|-------------|----------------|
| `docs/IMPLEMENTATION_GUIDE.md` | Modified | ~30 lines changed, ~90 lines added |

## Validation Results

### Forbidden Patterns (all 0 matches — PASS)

| Pattern | Matches |
|---------|---------|
| `252 steps` | 0 |
| `12 phases` | 0 |
| `Phase 11: Advanced Integrations` | 0 |
| `P9-P11` | 0 |
| `post-MVP` | 0 |

### Required Patterns (all present — PASS)

| Pattern | Matches |
|---------|---------|
| `23 phases` | 2 (header + grand total) |
| `Phase 11: WhatsApp` | 1 |
| `Phase 13: X Auto Poster` | 1 |
| `Stabilization` | 6+ |
| `Expansion` | 8+ |
| `Obscura CDP` | 4 (P13 spec + troubleshooting + services + ports) |

## Evidence Artifacts

- This verification file
- Modified `docs/IMPLEMENTATION_GUIDE.md` (grep verified)

## Doc-Sync Impact

- `docs/IMPLEMENTATION_GUIDE.md` is now consistent with canonical P0-P22 phase structure established by T1 (PROGRESS.md), T3 (CHECKLIST.md), T4 (StepPrompts.md)
- No cross-reference updates needed in other files (IMPLEMENTATION_GUIDE.md is self-contained system manual)

## Boundary Compliance

- No persona, consent, surveillance, or safety-affecting content modified
- No secrets, credentials, or personal data exposed
- P0-P8 content UNCHANGED
- P9-P10 step content UNCHANGED (only table labels updated)

## Rollback / Re-run Safety

- Re-run safe: all edits are idempotent string replacements
- Rollback: `git checkout -- docs/IMPLEMENTATION_GUIDE.md` restores previous version

## Design Decisions / Caveats

1. Phase table split into three sub-tables (MVP/Stabilization/Expansion) for readability — single 23-row table would be too dense
2. Grand total shows 233 + TBD (202 MVP + 31 Stabilization = 233 confirmed; Expansion TBD)
3. P10 step count updated from 18 to 19 per canonical binding decisions from T1/T3/T4
4. Expansion phase stubs are minimal — each will be fully specified at planner gate when ready for implementation
5. Cost column for Expansion phases marked TBD — actual costs determined during implementation planning

## Acceptance Criteria Mapping

| Criterion | Status |
|-----------|--------|
| Header updated to 23 phases | PASS |
| Phase table has P0-P22 | PASS |
| P9=12 steps, P10=19 steps | PASS |
| Old P11 section deleted | PASS |
| P11-P22 stubs added | PASS |
| P13 full spec included | PASS |
| No "post-MVP" references | PASS |
| No "252 steps" references | PASS |
| No "12 phases" references | PASS |
| P0-P8 unchanged | PASS |
| Evidence file created | PASS |

## Footer

Verified by direct grep and file read. All forbidden patterns absent, all required patterns present. File structure intact, no orphan references.
