# Auditor Report: Cross-File Consistency — P9+P10 Expansion

## Verdict: NEEDS REVIEW

StepPrompts.md has 3 stale metadata values not updated when P9 expanded from 12→13 steps and P10 from 19→21 steps. All other files are consistent with the new values.

---

## Per-File Checks

### 1. PROGRESS.md

| Check | Expected | Found | Pass? |
|-------|----------|-------|-------|
| P9 step count | 13 | `0/13` (Phase table), `(13 steps)` (section header), `P9-013` (step list) | ✅ |
| P10 step count | 21 | `0/21` (Phase table), `(21 steps)` (section header), `P10-021` (step list) | ✅ |
| Old "12 steps" for P9 | NOT present | Not found | ✅ |
| Old "19 steps" for P10 | NOT present | Not found | ✅ |
| "233" (old total) | NOT present | Not found | ✅ |
| "236" (new total) | Present | `180 / 236+`, `158/236+` | ✅ |
| "post-MVP" | NOT present | Not found | ✅ |
| Total phases | 23 (P0-P22) | `23 phases (P0-P22)` | ✅ |
| Stabilization total | 34 | `202 MVP + 34 Stabilization + TBD Expansion` | ✅ |

### 2. CHECKLIST.md

| Check | Expected | Found | Pass? |
|-------|----------|-------|-------|
| P9 step count | 13 | `P9-001 through P9-013 (13 steps)`, `All 13 steps verified` | ✅ |
| P10 step count | 21 | `P10-001 through P10-021 (21 steps)`, `All 21 steps verified` | ✅ |
| Old "12 steps" for P9 | NOT present | Not found | ✅ |
| Old "19 steps" for P10 | NOT present | Not found | ✅ |
| "233" (old total) | NOT present | Not found | ✅ |
| "236" (new total) | Present | Not found — CHECKLIST does not reference grand step total | ⚠️ NOTE |
| "post-MVP" | NOT present | Not found | ✅ |
| Total phases | 23 (P0-P22) | `23 phases (P0-P22)` (line 10) | ✅ |

### 3. IMPLEMENTATION_GUIDE.md

| Check | Expected | Found | Pass? |
|-------|----------|-------|-------|
| P9 step count | 13 | `\| P9 \| Financial Tracking \| 13 \|` (2 occurrences) | ✅ |
| P10 step count | 21 | `\| P10 \| Production Hardening \| 21 \|` (2 occurrences) | ✅ |
| Old "12 steps" for P9 | NOT present | Not found | ✅ |
| Old "19 steps" for P10 | NOT present | Not found | ✅ |
| "233" (old total) | NOT present | Not found | ✅ |
| "236" (new total) | Present | `236 + TBD` (grand total), `202 MVP + 34 Stabilization + TBD` | ✅ |
| "post-MVP" | NOT present | Not found | ✅ |
| Total phases | 23 (P0-P22) | `23 phases (P0-P22)` (3 occurrences) | ✅ |

### 4. StepPrompts.md

| Check | Expected | Found | Pass? |
|-------|----------|-------|-------|
| P9 step count in diagram (line 116) | 13 | `P9 Financial Tracking (12 steps, $1/mo)` | ❌ **FAIL** |
| P10 step count in diagram (line 117) | 21 | `P10 Production Hardening (19 steps, $1/mo)` | ❌ **FAIL** |
| P9-013 step header | Present | `### Step P9-013` (line 10959) | ✅ |
| P10-021 step header | Present | `### Step P10-021` (line 18731) | ✅ |
| P9+P10 `### Step P` headers | 34 | 13 P9 + 21 P10 = 34 | ✅ |
| "233" (old total) | NOT present | Not found | ✅ |
| "236" (new total) | Present | `systemd version >= 236` (P10-015 line 16006) — NOT a step count; no project total `236` | ⚠️ NOTE |
| "post-MVP" | NOT present | Not found | ✅ |
| Total phases | 23 (P0-P22) | `23 (P0-P22)` (line 11 and footer) | ✅ |
| Stabilization total in footer | 34 | `31 (Stabilization)` (line 19962) | ❌ **FAIL** |

---

## Findings

### F1 — Stale P9 step count in StepPrompts.md workflow diagram ❌

- **Location**: `stepprompts/StepPrompts.md`, line 116
- **Actual**: `P9  Financial Tracking (12 steps, $1/mo)`
- **Expected**: `P9  Financial Tracking (13 steps, $1/mo)`
- **Severity**: HIGH — contradicts P9-013 step header and all other 3 files

### F2 — Stale P10 step count in StepPrompts.md workflow diagram ❌

- **Location**: `stepprompts/StepPrompts.md`, line 117
- **Actual**: `P10 Production Hardening (19 steps, $1/mo)`
- **Expected**: `P10 Production Hardening (21 steps, $1/mo)`
- **Severity**: HIGH — contradicts P10-021 step header and all other 3 files

### F3 — Stale Stabilization total in StepPrompts.md footer ❌

- **Location**: `stepprompts/StepPrompts.md`, line 19962
- **Actual**: `Total Steps: 202 (MVP) + 31 (Stabilization) + TBD (Expansion)`
- **Expected**: `Total Steps: 202 (MVP) + 34 (Stabilization) + TBD (Expansion)` (13+21=34)
- **Severity**: MEDIUM — metadata only, does not affect step prompts themselves

### N1 — Additional stale values in StepPrompts.md diagram (out of scope) ⚠️

- **Location**: Lines 100, 104
- P1 shows `(20 steps)` — PROGRESS.md shows P1 = 21 steps
- P4 shows `(19 steps)` — PROGRESS.md shows P4 = 23 steps
- These are NOT part of this audit scope (P9/P10 only) but indicate a broader stale-diagram problem

### N2 — CHECKLIST.md has no grand total reference ⚠️

CHECKLIST.md does not reference "236" or any grand total step count. It does reference "23 phases (P0-P22)" which is correct. This is acceptable for a verification checklist whose primary concern is per-phase step verification, not aggregate counts.

### N3 — No "post-MVP" in any file ✅

All 4 files are clean — the old "post-MVP" terminology has been removed and replaced with "Stabilization" and "Expansion" categories.

---

## Verified Counts Summary

| Metric | Expected | PROGRESS.md | CHECKLIST.md | IMPL_GUIDE.md | StepPrompts.md | Consistent? |
|--------|----------|-------------|--------------|---------------|----------------|-------------|
| P9 steps | 13 | ✅ | ✅ | ✅ | ❌ (diagram: 12) | No |
| P10 steps | 21 | ✅ | ✅ | ✅ | ❌ (diagram: 19) | No |
| Stabilization total | 34 | ✅ | n/a | ✅ | ❌ (footer: 31) | No |
| Grand total | 236 + TBD | ✅ 236+ | n/a | ✅ 236+TBD | n/a | Yes |
| Phases | 23 (P0-P22) | ✅ | ✅ | ✅ | ✅ | Yes |
| `### Step P` P9+P10 | 34 | n/a | n/a | n/a | ✅ 34 | Yes |
| "post-MVP" | None | ✅ | ✅ | ✅ | ✅ | Yes |
| "233" (old) | None | ✅ | ✅ | ✅ | ✅ | Yes |

---

## Remediation Required

Three lines in `stepprompts/StepPrompts.md` need correction:

| Line | Current | Fix |
|------|---------|-----|
| 116 | `P9  Financial Tracking (12 steps, $1/mo)` | `P9  Financial Tracking (13 steps, $1/mo)` |
| 117 | `P10 Production Hardening (19 steps, $1/mo)` | `P10 Production Hardening (21 steps, $1/mo)` |
| 19962 | `31 (Stabilization)` | `34 (Stabilization)` |

---

## Out of Scope

- P3/P4/P5/P6/P7/P8 step counts — not part of this cross-file check
- P1 (line 100: 20 vs 21) and P4 (line 104: 19 vs 23) stale diagram values — separate issue outside P9/P10 scope
- `IMPLEMENTATION_GUIDE.md` P9 footnote: `P9 Financial Tracking (12 steps)` listed in earlier audit — NOT checked here (target files are the 4 specified)
- Actual content of step prompts (commands, verification, etc.) — scope is cross-file metadata consistency only
- $30 budget cap compliance — separate concern
- Whether "post-MVP" appears in any other file outside the 4 target files — scope limited to the 4 specified files
- P4-019b..P4-019e header renumbering consistency — out of scope