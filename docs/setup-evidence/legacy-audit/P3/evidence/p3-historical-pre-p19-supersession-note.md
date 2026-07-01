# P3 Historical Pre-P19 Supersession Note

**Date:** 2026-06-27
**Agent:** Read-only (parent, Opus 4.8)
**Purpose:** Mark pre-P19 reports as historical and point to current post-P19 rebaseline.

---

## Supersession Notice

The following P3 audit reports are now **HISTORICAL PRE-P19 SNAPSHOTS**. They were accurate when written (2026-06-25 / 2026-06-26) but are stale because P19 production schema was deployed to the live database on 2026-06-27.

### Superseded Reports

| Report | Date | Status | Current Replacement |
|---|---|---|---|
| `p3-current-live-db-reconciliation-audit.md` | 2026-06-26 | **HISTORICAL PRE-P19 SNAPSHOT** | `p3-post-p19-live-rebaseline.md` |
| `final-p3-implementation-audit-report.md` | 2026-06-25 | **HISTORICAL PRE-P19 SNAPSHOT** | `p3-post-p19-live-rebaseline.md` + `p3-post-p19-bug-reclassification.md` |
| `bug-register-all-severity.md` | 2026-06-25 | **HISTORICAL PRE-P19 SNAPSHOT** | `p3-post-p19-bug-reclassification.md` |
| `implementation-gap-register.md` | 2026-06-25 | **HISTORICAL PRE-P19 SNAPSHOT** | `p3-post-p19-bug-reclassification.md` |
| `superseded-transition-register.md` | 2026-06-25 | **HISTORICAL PRE-P19 SNAPSHOT** | `p3-post-p19-bug-reclassification.md` |

### What Changed

| Old Fact (pre-P19) | New Fact (post-P19) |
|---|---|
| P19 not deployed. Alembic current = p20_001. | P19 IS deployed. Alembic has 4 versions: p19_001, p19_002, p19_003, p20_001. |
| 0 project_id columns in memory schema. | 8 project_id columns in memory schema. 5 NOT NULL. |
| 0 project_scope columns anywhere. | 4 project_scope columns in memory schema. All NOT NULL DEFAULT 'project'. |
| projects.project_registry does not exist. | EXISTS. Default project seeded (id=00000000-0000-0000-0000-000000000001, slug=default). |
| session_summaries has 7 columns. | 8 columns (project_id NOT NULL added). Still missing 11 ClassificationMetaMixin columns. |
| BUG-005 "4 btree DESC indexes missing" = REFUTED_BY_LIVE_DB. | Still refuted. All 4 exist. |
| BUG-003/BUG-008/BUG-018 "moot because P19 not deployed." | Now LIVE BUGS. P19 deployed, project_id exists, but source code doesn't use it. |
| BUG-008 = HIGH (consolidation has zero project awareness). | ESCALATED to CRITICAL. semantic_facts.project_id is now NOT NULL. Consolidation will crash without project_id. |
| "P19 not deployed" claims throughout all 5 reports. | Superseded. P19 is deployed and verified on live VPS. |

### Current Reports (Post-P19)

| Report | Purpose |
|---|---|
| `p3-post-p19-live-rebaseline.md` | Current live DB truth after P19 production deploy. Ground truth for all future P3 work. |
| `p3-post-p19-bug-reclassification.md` | All 67 P3 bugs reclassified against post-P19 live state. |
| `p3-historical-pre-p19-supersession-note.md` | This file. |
| `p3-post-p19-audit-round-1.md` | Independent auditor verification of rebaseline + reclassification. |
| `p3-post-p19-audit-round-2.md` | Re-audit of round 1 findings. |

---

## How to Read P3 Evidence

1. **For current live truth:** Read `p3-post-p19-live-rebaseline.md`.
2. **For bug status:** Read `p3-post-p19-bug-reclassification.md`.
3. **For historical context:** The old reports remain valid as historical records of what was true before P19 deploy.
4. **For P19 deploy details:** Read `docs/setup-evidence/P19/evidence/production-deploy/p19-012-final-production-report.md`.

---

## Explicit Affirmation

No source code modified. No DB writes. No migration. No deploy. No restart. Historical note only.

**Output file:** `docs/setup-evidence/legacy-audit/P3/evidence/p3-historical-pre-p19-supersession-note.md`