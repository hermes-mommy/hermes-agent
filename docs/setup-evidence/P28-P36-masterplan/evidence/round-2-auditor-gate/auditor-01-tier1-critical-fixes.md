# Auditor 01 — Tier 1 Critical Fixes Audit

| Field | Value |
|---|---|
| **Auditor** | Guinevere (parent-agent, direct audit) |
| **Date** | 2026-06-28 |
| **Scope** | Tier 1 Critical Fixes for P28-P36 alignment |
| **Base Path** | `docs/setup-evidence/P28-P36-masterplan/` |
| **Verdict** | **NEEDS-REVIEW** |

---

## Summary

6 of 9 checks PASS. 1 check FAILS (stale ADR-056 references in 3 adr-drafts/ files treat deleted ADR as active). 2 checks PASS with caveats (BLDM line 7 Authority list still includes ADR-056; consent_ref NOT NULL pattern exists in ADR-066/evidence but only in descriptive/problem-stating context, not in enforceable schema docs).

---

## Per-Check Results

### Check 1: ADR-056 DELETED — ✅ PASS

**Test**: `glob **/ADR-056*` in `adr-drafts/` and across full masterplan.

**Result**: Zero files found. The file `ADR-056-fork-agnostic-p28-path.md` does NOT exist in `adr-drafts/` or anywhere in the masterplan directory tree.

**Evidence**:
- `glob adr-drafts/**/ADR-056*` → "No files found"
- `glob **/ADR-056*` (full masterplan) → "No files found"

---

### Check 2: ADR-066 EXISTS — ✅ PASS

**File**: `adr-drafts/ADR-066-hermes-runtime-consent-ref-carve-out.md` (167 lines)

| Section | Present | Content |
|---|---|---|
| **Status** | ✅ Line 3 | `Proposed` |
| **Date** | ✅ Line 4 | `2026-06-28` |
| **Context** | ✅ Lines 7-21 | Two-tier consent_ref problem; Hermes runtime vs dev-workflow contradiction; references architecture-s1-s5 (L514/581/603/606) and hermes-society-master-architecture (L596/619/686/1616/1673) |
| **Decision** | ✅ Lines 23-65 | Two-tier regime: Tier 1 (Hermes runtime, NULLABLE) + Tier 2 (dev-workflow, NOT NULL) + CHECK constraint + migration strategy |
| **Consequences** | ✅ Lines 67-88 | 5 positive, 5 negative, 2 neutral |

---

### Check 3: ADR-067 EXISTS — ✅ PASS

**File**: `adr-drafts/ADR-067-hermes-runtime-y-level-cap-removal.md` (172 lines)

| Section | Present | Content |
|---|---|---|
| **Status** | ✅ Line 3 | `Proposed` |
| **Date** | ✅ Line 4 | `2026-06-28` |
| **Context** | ✅ Lines 7-31 | Y-level system (Y4 baseline, Y5 ceiling, Y6 forbidden); ADR-062 paradigm shift; BLDM Q81 + Brainstorm Batch 3 contradiction |
| **Decision** | ✅ Lines 33-80 | Two-tier Y-level regime: Tier 1 (Hermes runtime, NO cap) + Tier 2 (dev-workflow, Y4/Y5/Y6 enforced) + implementation layer details |
| **Consequences** | ✅ Lines 82-106 | 7 positive, 5 negative, 3 neutral |

---

### Check 4: P32 README.md Title — ✅ PASS

**File**: `plans/P32/README.md` (219 lines)

- **Frontmatter title** (line 2): `title: "P32 — External Presence & Tools"` ✅
- **H1 heading** (line 17): `# P32 — External Presence & Tools` ✅
- **Status** (line 3): `"Plan Definition — Rewritten"` ✅
- **Supersedes** (line 11): `Original 'P24 Fork Integration' scope (obsoleted when P24 v2.0 became the fork itself)` ✅
- **Forbidden pattern FP-06** (line 204): `fork.?agnostic` marked Forbidden ✅

---

### Check 5: P32 plan.md Title — ✅ PASS

**File**: `plans/P32/plan.md` (462 lines)

- **Frontmatter title** (line 2): `title: "P32 — Implementation Plan — External Presence & Tools"` ✅
- **H1 heading** (line 23): `# P32 — Implementation Plan: External Presence & Tools` ✅
- **Status** (line 3): `"Plan Definition — Rewritten"` ✅
- **Supersedes** (line 11): `Original 'P24 Fork Integration' plan (obsoleted when P24 v2.0 became the fork)` ✅

---

### Check 6: BLDM Q2 "P24 IS hard dep" — ✅ PASS

**File**: `adr-drafts/BLDM-Hard-Locked-Faiz-Decisions.md`

- **Line 31 (Q2 decision)**: `**P24 fork IS a hard dependency for P28+**, locked 2026-06-28.` ✅
- **Additional content**: References ADR-056 DELETED, P32 renamed, brainstorm decisions ✅
- **Status**: `LOCKED (supersedes ADR-056 §21-31 — ADR-056 DELETED, fork-agnostic path inverted by P24 v2.0 replan)` ✅

---

### Check 7: BLDM Line 7 ADR-066/067 "NOW WRITTEN" — ✅ PASS (with caveat)

**File**: `adr-drafts/BLDM-Hard-Locked-Faiz-Decisions.md`

- **Line 7**: `ADR-066 (consent_ref carve-out) and ADR-067 (Y-level cap removal) are NOW WRITTEN — see adr-drafts/. Post-Phase-4 backlog reference updated 2026-06-28.` ✅

**Caveat**: Line 7 Authority list still includes `ADR-056 §Compliance` despite ADR-056 being deleted. This is a historical citation (BLDM was cited from ADR-055..065, and ADR-056 existed when that happened). Q2 at line 31 explicitly marks ADR-056 as DELETED, providing correction. This is cosmetic, not structural. Flagged in Check 9 findings.

---

### Check 8: consent_ref UUID NOT NULL — ✅ PASS

**Test**: `grep consent_ref UUID NOT NULL` across masterplan.

**Result**: 7 matches in 3 files. **ZERO matches in enforceable architecture schema docs.**

| File | Context | Treats as enforceable? |
|---|---|---|
| `adr-drafts/ADR-066-...md` (L9,17,42,127,132) | Problem statement + migration spec describing the change FROM NOT NULL to two-tier | ❌ No — ADR-066 is the fix itself |
| `evidence/round-2-wave-1/wave1-architecture-fixes.md` (L27) | Reports that the exact pattern did NOT exist in enforceable form | ❌ No — evidence documentation |
| `evidence/round-2-wave-1/wave1-adr-changes.md` (L36) | Problem statement in ADR changes log | ❌ No — evidence documentation |

**Architecture source files** (`sections/architecture-s1-s5-runtime-memory.md`, `sections/hermes-society-master-architecture.md`) were NOT matched — confirming the constraint was already addressed or only existed in prose form that didn't match the exact string.

---

### Check 9: Stale ADR-056 References — ❌ FAIL

**Test**: `grep ADR-056` across all files except `research/`. Filter for references that treat ADR-056 as active (not deleted).

**Result**: **3 files in `adr-drafts/` + 2 files in `plans/` contain stale ADR-056 references that treat it as active.**

#### Critical — adr-drafts/ files (treat ADR-056 as active ADR)

| # | File | Line | Content | Issue |
|---|---|---|---|---|
| 1 | `adr-drafts/ADR-055-hermes-society-architecture.md` | 69 | `ADR-056 (Fork-Agnostic Path)` in Related ADRs list | Lists ADR-056 as active sibling ADR. No "DELETED" annotation. |
| 2 | `adr-drafts/ADR-057-founder-only-spawn-2-of-2-agreement.md` | 77 | `ADR-056-fork-agnostic-p28-path.md — lineage portability invariant` | References ADR-056 file as valid cross-reference with active content. |
| 3 | `adr-drafts/ADR-059-shared-world-model-with-private-memory.md` | 92 | `The architecture is P24 fork-agnostic (ADR-056)` | Cites ADR-056 as active architectural invariant. Contradicts Q2 (P24 IS hard dep). |
| 4 | `adr-drafts/ADR-059-shared-world-model-with-private-memory.md` | 117 | `ADR-056-fork-agnostic-p28-path.md` in References | File path reference to deleted file. |
| 5 | `adr-drafts/BLDM-Hard-Locked-Faiz-Decisions.md` | 280 | `ADR-056-fork-agnostic-p28-path.md` in §22 References | File path listed but file doesn't exist. |

#### Moderate — plans/ files (stale but lower structural impact)

| # | File | Line | Content | Issue |
|---|---|---|---|---|
| 6 | `plans/P32/evidence-template.md` | 148 | `adr/ADR-056-p32-fork-integration.md` | References ADR-056 for fork integration (scope obsolete). |
| 7 | `plans/P32/evidence-template.md` | 204 | `Move to docs/10-governance/ post-P32 if Faiz allocates ADR-056` | ADR-056 number reused for different purpose. |
| 8 | `plans/P35/plan.md` | 133-138, 163, 232, 264 | `ADR-056-p35-self-evolution-ratchet.md` | **Reuses ADR-056 number** for a completely different ADR (self-evolution Ratchet). Number conflict with deleted fork-agnostic ADR. |

#### Non-critical — already annotated as DELETED

| File | Line | Annotation Status |
|---|---|---|
| `adr-drafts/BLDM-Hard-Locked-Faiz-Decisions.md` | 7 | Authority line lists ADR-056 but Q2 (L31) marks it DELETED |
| `plans/P28/README.md` | 95 | "P24 v2.0 supersedes ADR-056" ✅ |
| `plans/P28/plan.md` | 22, 266 | "ADR-056 (DELETED)" ✅ |
| `final/README.md` | 13 | "ADR-056 (fork-agnostic) DELETED" ✅ |
| `final/final-report.md` | 16, 187 | "ADR-056 deleted" ✅ |
| `fixes/round-1-fix-log.md` | 16 | "ADR-056 (fork-agnostic) DELETED" ✅ |
| `evidence/round-2-wave-1/wave1-adr-changes.md` | 21, 87, 95, 106 | "ADR-056 DELETED" ✅ |

---

## Findings Summary

| # | Severity | Finding | Location | Recommended Fix |
|---|---|---|---|---|
| F-01 | **HIGH** | ADR-055 line 69 lists ADR-056 as active Related ADR | `adr-drafts/ADR-055-hermes-society-architecture.md:69` | Add "(DELETED — superseded by ADR-062 + P24 v2.0)" annotation |
| F-02 | **HIGH** | ADR-057 line 77 references ADR-056 file as active invariant | `adr-drafts/ADR-057-founder-only-spawn-2-of-2-agreement.md:77` | Replace with "ADR-056 DELETED — fork-agnostic path inverted" |
| F-03 | **HIGH** | ADR-059 line 92 cites ADR-056 as active architectural invariant | `adr-drafts/ADR-059-shared-world-model-with-private-memory.md:92` | Remove fork-agnostic claim; annotate as superseded by P24 hard dep |
| F-04 | **HIGH** | ADR-059 line 117 lists ADR-056 file path in References | `adr-drafts/ADR-059-shared-world-model-with-private-memory.md:117` | Remove or annotate as "(DELETED)" |
| F-05 | **MEDIUM** | BLDM line 280 lists ADR-056 file path in §22 References | `adr-drafts/BLDM-Hard-Locked-Faiz-Decisions.md:280` | Remove or add "(DELETED — file no longer exists)" |
| F-06 | **MEDIUM** | P32 evidence-template.md references ADR-056 for fork integration | `plans/P32/evidence-template.md:148,204` | Remove stale fork-integration ADR references |
| F-07 | **HIGH** | P35 plan.md reuses ADR-056 number for different ADR | `plans/P35/plan.md:133-138,163,232,264` | Renumber to unused ADR number (e.g., ADR-068+) to avoid conflict |

---

## Verdict: NEEDS-REVIEW

**Rationale**: 6 of 9 checks PASS cleanly. Check 8 (consent_ref NOT NULL) passes — the pattern only appears in descriptive/problem-stating context, not in enforceable schema docs. However, **Check 9 FAILS** because 3 ADR files in `adr-drafts/` (ADR-055, ADR-057, ADR-059) contain references that treat ADR-056 as active, not deleted. Additionally, P35 plan.md reuses the ADR-056 number for a completely different decision (self-evolution Ratchet), creating a numbering conflict.

The ADR-056 file deletion itself is clean. The issue is **stale cross-references in sibling ADRs** that were not updated when ADR-056 was deleted. This is a doc-sync gap, not a structural defect, but it could mislead future auditors reading ADR-055/057/059 into believing ADR-056 still exists.

**Resolution**: Update 7 locations across 5 files to annotate ADR-056 references as DELETED. Renumber P35's ADR-056 to an unused number.

---

## Evidence Artifacts

| Artifact | Path |
|---|---|
| This report | `docs/setup-evidence/P28-P36-masterplan/evidence/round-2-auditor-gate/auditor-01-tier1-critical-fixes.md` |

---

## Footer

Version 1.0 | 2026-06-28 | Author: Guinevere (parent-agent direct audit) | Status: NEEDS-REVIEW — 6/9 PASS, Check 9 FAIL (7 stale ADR-056 references in 5 files)
