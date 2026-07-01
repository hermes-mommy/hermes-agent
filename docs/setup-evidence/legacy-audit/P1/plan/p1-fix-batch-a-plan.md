# P1 Fix Batch A — Implementation Plan

**Date:** 2026-06-26
**Scope:** Source + docs only, no deploy, no restart
**Source of truth:** P1 live-vps-reconciliation-audit.md

---

## Research Findings

### ContextCompactor (src/memory/compaction.py)
- **Usage:** Exported in `src/memory/__init__.py:68,282` (import + `__all__`)
- **Instantiation:** NEVER — zero `ContextCompactor()` calls anywhere in codebase
- **Tests:** None
- **References:** Only in historical P20 evidence docs (verification.md)
- **Verdict:** Truly dead code. Mark deprecated with `DeprecationWarning` on `__init__`. Do NOT delete (exported API, future P19 may use it).

### sandbox.py (src/loops/sandbox.py)
- **Bug:** Lines 345, 351 use `re.search()` and `re.finditer()` but no `import re`
- **Impact:** Would raise `NameError` if `_parse_pytest_output()` is called
- **Fix:** Add `import re` to standard library imports

### main.py (src/core/main.py)
- **Line 97:** `loop_manager = LoopManager(llm_router=None)`
- **Missing:** No comment explaining why router is None
- **Fix:** Add explanatory comment referencing P20/HermesBrain path

---

## Implementation Plan

### Phase 1: Source Fixes (parallel)

| ID | File | Action | Restart? | Test? |
|----|------|--------|----------|-------|
| S1 | `src/loops/sandbox.py` | Add `import re` after `import subprocess` | No | AST parse |
| S2 | `src/core/main.py` | Add comment at line 97 explaining `llm_router=None` | No | AST parse |
| S3 | `src/memory/compaction.py` | Add `DeprecationWarning` on `ContextCompactor.__init__` | No | AST parse |

### Phase 2: Docs/Evidence Fixes (parallel after source)

| ID | File | Action |
|----|------|--------|
| D1 | `docs/setup-evidence/P1/STEP-P1-018/evidence.md` | Append hardening note |
| D2 | `PROGRESS.md` | Fix P1-021 test count 142→70 with footnote |
| D3 | `CHECKLIST.md` | Fix "20 steps" → "21 steps" |
| D4 | `docs/setup-evidence/P1/STEP-P1-008/` through `STEP-P1-011/` | Create stub dirs with README.md |
| D5 | 3 UTF-16LE files | Convert to UTF-8 |

### Phase 3: Verification (sequential after all fixes)

| ID | Check | Command |
|----|-------|---------|
| V1 | AST parse all 3 source files | `python -c "import ast; ast.parse(open('...').read())"` |
| V2 | Secret scan on changed files | `grep -rnE 'sk-[a-zA-Z0-9]{20,}|...'` |
| V3 | Grep for `import re` in sandbox.py | Verify present |
| V4 | Grep for DeprecationWarning in compaction.py | Verify present |
| V5 | Re-count PROGRESS.md test count | Verify 70/70 |
| V6 | Re-count CHECKLIST steps | Verify "21 steps" |
| V7 | Verify 4 new STEP dirs exist | Verify P1-008 through P1-011 |
| V8 | `file` command on 3 UTF-16 files | Verify UTF-8 |

### Phase 4: Audit + Final Evidence

---

## Hard Rejection Criteria
- Any deploy/restart/SSH mutation: FAIL
- Any secret printed: FAIL
- Any deletion of ContextCompactor (only deprecation allowed): FAIL
- Incomplete evidence: FAIL