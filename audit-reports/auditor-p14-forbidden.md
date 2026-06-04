# P14 Wearable Forbidden Patterns + Scope Audit

**Date:** 2026-06-04  
**Scope:** 27 files in `research-reports/p14-expansion/P14-*.md`  
**Verdict:** **FAIL**

---

## Summary

| # | Pattern | Matches | Status |
|---|---------|---------|--------|
| 1 | `post-MVP` | 0 | PASS |
| 2 | Type suppression (`# type: ignore`, `@ts-ignore`, `@ts-expect-error`, `as any`) | 23 | **FAIL** |
| 3 | Empty catch (`except Exception: pass`) | 1 | **FAIL** |
| 4 | `TODO`/`TBD` placeholder | 0 | PASS |
| 5 | Baileys references (scope) | 0 | PASS |
| 6 | Node.js runtime references (scope) | 0 | PASS |
| 7 | Redis wearable session storage (scope) | 0 | PASS |

**Total violations: 24** — exceeds FAIL threshold (4+).

---

## Detailed Findings

### Pattern 1: `post-MVP` — PASS

Zero matches across all 27 files. No file uses the deprecated `post-MVP` terminology.

---

### Pattern 2: Type Suppression — FAIL (23 violations)

**NOT flagged:** Checklist items in P14-010.md:503, P14-019.md:346, P14-020.md:450, and P14-021.md:515 that reference type suppression patterns as verification criteria. These are audit requirements, not actual code violations.

#### P14-011.md — 4 instances of `# type: ignore[arg-type]`

All four are in the scoring engine code samples (`score_sleep_pillar`, `score_cardio_pillar`, `score_activity_pillar`, `score_recovery_pillar`):

| Line | Context |
|------|---------|
| 269 | `score=_clamp(score, 0.0, 100.0),  # type: ignore[arg-type]` (sleep pillar) |
| 321 | `score=_clamp(score, 0.0, 100.0),  # type: ignore[arg-type]` (cardio pillar) |
| 356 | `score=_clamp(score, 0.0, 100.0),  # type: ignore[arg-type]` (activity pillar) |
| 399 | `score=_clamp(score, 0.0, 100.0),  # type: ignore[arg-type]` (recovery pillar) |

**Root cause:** `_clamp()` returns `float`, but `PillarScore.score` expects `int`. The code does `int(round(...))` before calling but `_clamp` returns float — proper fix is to make `_clamp` return `int` or cast inline.

#### P14-012.md — 19 instances of `# type: ignore[arg-type]`

All 19 are in the `DailySummary` construction code block (lines 498-516), where dict `.get()` returns `Optional[X]` but `DailySummary` fields expect non-optional types:

| Line | Example |
|------|---------|
| 498 | `sleep_duration_min=sleep.get("sleep_duration_min"),  # type: ignore[arg-type]` |
| 499 | `sleep_quality=sleep.get("sleep_quality"),  # type: ignore[arg-type]` |
| 500-516 | (17 more identical patterns for health metric fields) |

**Root cause:** Type annotations on `DailySummary` fields don't accept `Optional`, but dict `.get()` return is `Optional`. Fix: add explicit defaults (e.g., `sleep.get(...) or 0.0`) or annotate `DailySummary` fields as `Optional`.

---

### Pattern 3: Empty Catch — FAIL (1 violation)

#### P14-012.md line 680-681 — Rollback/Demolition section

```python
# Remove APScheduler job:
try:
    scheduler.remove_job(SUMMARY_JOB_ID)
except Exception:
    pass
```

**Context:** This is in the `## Rollback / Demolition` section showing cleanup code. While arguably intentional (if job doesn't exist, don't crash cleanup), it matches the forbidden pattern exactly (`except Exception:` followed by `pass`).

**All other except blocks verified clean** — every other `except` block in the P14 files has proper `logger.exception(...)` logging (P14-006, P14-007, P14-008, P14-009, P14-015, P14-016, P14-021). None are bare/empty catches.

---

### Pattern 4: `TODO`/`TBD` — PASS

Zero matches across all 27 files.

---

### Pattern 5: Baileys References (Scope) — PASS

Zero matches. P14 files make no reference to the Baileys WhatsApp library.

---

### Pattern 6: Node.js Runtime References (Scope) — PASS

Zero matches. P14 files reference no Node.js/npm/JavaScript runtime. All code is Python.

---

### Pattern 7: Redis Wearable Session Storage (Scope) — PASS

Redis IS referenced in 2 files, but for infrastructure purposes — NOT for wearable data session storage:

- **P14-007.md** (5 refs): Redis used for **consent scope storage** (`consent:scopes:surveillance.wearable.health.explicit` in DB2), which is the standard consent management infrastructure — not wearable data storage.
- **P14-006.md** (2 refs): Redis used as a **message buffer** for the surveillance event pipeline — standard infrastructure, not wearable data storage.

All wearable telemetry data (heart rate, sleep, activity, SpO2, HRV) is stored in PostgreSQL/TimescaleDB `health.*` hypertables per the design. No Redis-based session storage for wearable data exists in any P14 file.

---

## Verdict: FAIL

**24 forbidden pattern violations** across 2 files (P14-011 and P14-012):

| File | Pattern 2 | Pattern 3 | Total |
|------|-----------|-----------|-------|
| P14-011.md | 4 | 0 | 4 |
| P14-012.md | 19 | 1 | 20 |
| **Total** | **23** | **1** | **24** |

**Recommended fixes:**

1. **P14-011.md:** Replace `# type: ignore[arg-type]` on `PillarScore(score=...)` with either `int(_clamp(...))` cast or modify `_clamp` to return `int`.

2. **P14-012.md:** 
   - Replace all 19 `# type: ignore[arg-type]` with explicit defaults: `sleep.get("sleep_duration_min") or 0` or annotate `DailySummary` fields as `Optional[float]`.
   - Replace empty `except Exception: pass` with `except Exception: logger.warning("scheduler_remove_job_failed")` or more targeted exception class.

---

## Files Audited (27)

P14-001 through P14-027 (all files in `research-reports/p14-expansion/P14-*.md`).