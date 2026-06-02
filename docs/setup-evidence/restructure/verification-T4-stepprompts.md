# T4 Verification — StepPrompts.md Phase Restructure

**Task:** T4 — StepPrompts.md Phase Restructure
**Date:** 2026-06-03
**File Modified:** `stepprompts/StepPrompts.md`
**Status:** PASS

## What Was Done

### Header Updates
- `Total Steps: 252` → `Total Steps: 202 (MVP) + 31 (Stabilization) + TBD (Expansion)`
- `Total Phases: 12 (P0-P11)` → `Total Phases: 23 (P0-P22)`

### Shared VPS Note
- `P3-P7, P9-P11` → `P3-P7, P9-P22`

### Step ID Convention
- Phase range `0-11` → `0-22`

### Phase Dependency Graph
- Complete rewrite of ASCII diagram to include P9-P22 with dependency annotations
- Stabilization label for P9-P10, Expansion label for P11-P22
- Each expansion phase shows its specific dependency chain

### Phase 9: Financial Tracking
- Header: `(Post-MVP)` → `(Stabilization)`
- Design Decision note: `Phases 9-11` → `Phases 9-10`, `post-MVP` → `Stabilization`
- All P9-001 to P9-012 steps kept intact

### Phase 10: Production Hardening
- Header: `(Post-MVP)` → `(Stabilization)`
- Step Count: `18` → `19`
- Steps header: `P10-001 to P10-018` → `P10-001 to P10-019`
- Added P10-019: MVP Acceptance Gate step in the main step list
- Evidence path updated to P10-019
- P10-018b gate section preserved; its gate reference updated from "Phase 11 (Post-MVP)" to "Expansion phases (P11-P22)"

### Phase 11 Replacement
- DELETED entire old "Phase 11: Advanced Integrations (Post-MVP)" section (P11-001 to P11-025)
- REPLACED with 12 new phase stubs (P11-P22), each containing:
  - Goal, Steps (TBD), Dependencies, Cost (TBD), Evidence Path
  - Steps placeholder, Phase Complete Criteria, Verification section
- P13 (X Auto Poster) includes expanded spec with Key Components:
  - Obscura CDP, S3 Queue, LLM Captions, 3h Heartbeat, Discord Notifications, PostgreSQL State

### Phase Transition Checklists
- `Before P8 → P9 (Post-MVP Gate)` → `Before P8 → P9 (Stabilization Gate)`
- `Before P9 → P10 → P11` → Split into:
  - `Before P9 → P10 (Stabilization Transition)`
  - `Before P10 → P11 (Expansion Gate)`

### Parallel Work Guide
- Replaced P10/P11 conflict row with:
  - P11-P22 (Expansion) can run parallel with each other
  - P11-P22 (Expansion) cannot run parallel with their dependencies

### Budget Tracking Summary
- P9/P10 rows now labeled (Stabilization)
- P11 row replaced with P11-P22 (Expansion) TBD row
- Total row updated to MVP+Stab only

### MVP Acceptance Gate
- `Phase 11 (Post-MVP)` → `Expansion phases (P11-P22)`

### Footer
- Version bumped to v1.1, date updated to 2026-06-03
- Step count and phase count updated

## Files Changed

| File | Change Type |
|------|------------|
| `stepprompts/StepPrompts.md` | Modified (multiple sections) |

## Validation Results

### Forbidden Patterns (must be 0 matches)

| Pattern | Matches | Status |
|---------|---------|--------|
| `Total Phases: 12` | 0 | PASS |
| `Total Steps: 252` | 0 | PASS |
| `Phase 11: Advanced Integrations` | 0 | PASS |
| `P9-P11` | 0 | PASS |
| `post-MVP` | 0 | PASS |

### Required Patterns (must be ≥1 match)

| Pattern | Matches | Status |
|---------|---------|--------|
| `Total Phases: 23` | 1 (footer) | PASS |
| `Phase 11: WhatsApp` | 1 | PASS |
| `Phase 13: X Auto Poster` | 1 | PASS |
| `Stabilization` | 11 | PASS |
| `Expansion` | 22 | PASS |
| `Obscura CDP` | 7 (incl. P13 spec) | PASS |

## Evidence Artifacts
- This file: `docs/setup-evidence/restructure/verification-T4-stepprompts.md`

## Doc-Sync Impact
- `stepprompts/StepPrompts.md` is now the canonical phase reference for P0-P22
- Other files referencing "P11" or "12 phases" may need separate updates (out of T4 scope)

## Boundary Compliance
- No persona drift, consent violation, surveillance overreach
- No Y6, no HARD STOP bypass, no distress protocol suppression
- No secret/intimate data exposure

## Rollback/Re-run Safety
- File can be reverted via git if available
- No destructive operations performed
- All changes are text-level edits to a single markdown file

## Design Decisions/Caveats
- P10-019 added as a distinct step in the main list (separate from P10-018b gate)
- Expansion phase stubs use uniform template format for consistency
- P13 X Auto Poster has expanded Key Components section per task spec
- Header "Total Phases: 23" uses bold markdown (`**Total Phases:**`) — grep pattern matches footer unbolded version

## Acceptance Criteria Mapping

| Criterion | Status |
|-----------|--------|
| Header counts updated | PASS |
| Shared VPS note updated | PASS |
| Step ID Convention updated | PASS |
| Dependency graph rewritten | PASS |
| P9 headers updated | PASS |
| P10 headers + P10-019 added | PASS |
| Old P11 deleted, P11-P22 stubs created | PASS |
| P13 detailed spec included | PASS |
| Transition checklists updated | PASS |
| Parallel work guide updated | PASS |
| Budget tracking updated | PASS |
| MVP gate reference updated | PASS |
| Footer updated | PASS |
| Zero forbidden patterns | PASS |
| All required patterns found | PASS |
| P0-P8 unchanged | PASS |

---

*T4 Verification Complete — All checks PASS*
