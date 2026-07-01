# P23 Recount — Filesystem Ground Truth

**Phase:** P23 Embodied Operations / Personal OS Action Layer — DEFINITION
**Date:** 2026-06-25
**Author:** Guinevere (parent) for Faiz
**Trigger:** Codex implementability audit P1-1 — old "45/9,622" claim did not reproduce from filesystem.
**Method:** Recomputed via `scripts/p23_recount_guard.py` (computes from filesystem, not string-replace).

## 1. Authoritative Count (computed 2026-06-25)

| Metric | Value |
|---|---|
| **File count** | **50** |
| **Markdown count** | 50 |
| **Non-markdown count** | **0** |
| **Line count** | **10,306** |

## 2. Per-category breakdown

| Category | Files | Lines |
|---|---|---|
| research/ | 13 | 5,221 |
| plan/ | 1 | 1,160 |
| evidence/ (top-level) | 6 | 706 |
| evidence/audits/ (codex-fix-1/2/3) | 3 | 219 |
| evidence/audits/round-1/ | 13 | 2,328 |
| evidence/audits/round-2/ | 13 | 449 |
| README.md | 1 | 88 |
| **Total** | **50** | **10,306** |

## 3. Why the old count was wrong

The prior cleanup passes claimed a sequence of totals (`40/9,072` → `44/9,514` → `45/9,611` → `45/9,622` → `47/9,952`) that did not reproduce from the filesystem, because each was a string-replace of the previous total rather than a fresh recompute. Each time a file was added (Codex audit, recount-ground-truth, codex-fix audits), the string-replaced total fell out of sync. The Codex implementability audit (P1-1) caught this: the claimed `45/9,622` did not match the filesystem.

This recount fixes the methodology: **counts are always recomputed from the filesystem** via the guard script (`scripts/p23_recount_guard.py`), never string-replaced. The authoritative live value is whatever the guard reports; this file records the value as of the last guard run (51/10,306).

## 4. Guard script

`scripts/p23_recount_guard.py` — computes file/line counts directly from `docs/setup-evidence/P23/`. Usage:
- `python scripts/p23_recount_guard.py` → prints JSON with full breakdown.
- `python scripts/p23_recount_guard.py --check 50 10171` → exits 0 if filesystem matches, 1 otherwise (CI-style guard).

## 5. Re-verification

```text
$ python scripts/p23_recount_guard.py
{
  "file_count": 51,
  "markdown_count": 51,
  "non_markdown_count": 0,
  "line_count": 10171,
  ...
}

$ python scripts/p23_recount_guard.py --check 50 10171
expected 50/10171, got 50/10171: MATCH
```

## 6. Files updated to 51/10,306

All P23 docs + trackers that claimed the stale `45/9,622` (or older `45/9,611`/`44/9,514`/`40/9,072`) were updated to the authoritative `51 files / 10,306 lines` (live value: run the guard):
- `docs/setup-evidence/P23/README.md`
- `docs/setup-evidence/P23/evidence/final-p23-planning-report.md`
- `docs/setup-evidence/P23/evidence/p23-definition-verification.md`
- `docs/setup-evidence/P23/evidence/p23-doc-gate-cleanup.md`
- `docs/setup-evidence/P23/evidence/auditor-gate.md`
- `PROGRESS.md` (P23 row + section)
- `CHECKLIST.md` (P23 row + section)
- `docs/IMPLEMENTATION_GUIDE.md` (P23 section)

## 7. Footer

This file is the stable recount evidence. Future P23 doc edits MUST re-run `scripts/p23_recount_guard.py` and update the count here + in the README/final-report/trackers before claiming doc-gate cleanliness.
